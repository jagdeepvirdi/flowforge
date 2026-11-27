"""Optional reversible token lookup: storage, retention, the admin-only audited API, and reconcile."""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import bcrypt
import pytest
from click.testing import CliRunner
from sqlalchemy import text

from flowforge import token_store
from flowforge.crypto import decrypt_value
from flowforge.db.models import AuditLog, TokenMap, User, db
from flowforge.steps.reconcile import ReconcileStep
from flowforge.tokenization import tokenize

MSISDN = '15550001234'
OTHER = '15550009999'
UNKNOWN = 'tk_msisdn_' + '0' * 32


@pytest.fixture(autouse=True)
def _clean(app):
    def wipe():
        with app.app_context():
            db.session.query(TokenMap).delete()
            db.session.commit()
    wipe()
    yield
    wipe()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# -- storage ------------------------------------------------------------------------------

def test_remember_and_reveal_roundtrip(ctx):
    t1, t2 = tokenize(MSISDN), tokenize('001010000000001', 'imsi')
    assert token_store.remember_many([('msisdn', t1, MSISDN), ('imsi', t2, '001010000000001')]) == 2
    got = token_store.reveal([t1, t2, UNKNOWN])
    assert got[t1] == {'kind': 'msisdn', 'value': MSISDN}
    assert got[t2] == {'kind': 'imsi', 'value': '001010000000001'}
    assert got[UNKNOWN] is None


def test_original_is_stored_only_as_ciphertext(ctx):
    t = tokenize(MSISDN)
    token_store.remember_many([('msisdn', t, MSISDN)])
    raw = db.session.execute(text('select token, kind, ciphertext from ff_token_map')).one()
    assert raw.token == t and raw.kind == 'msisdn'
    assert MSISDN not in raw.ciphertext and MSISDN not in str(tuple(raw))
    assert decrypt_value(raw.ciphertext) == MSISDN


def test_seeing_a_token_again_refreshes_last_seen_without_duplicating(ctx):
    t = tokenize(MSISDN)
    token_store.remember_many([('msisdn', t, MSISDN)])
    first = db.session.query(TokenMap).one()
    created, seen, cipher = first.created_at, first.last_seen_at, first.ciphertext
    db.session.expire_all()
    token_store.remember_many([('msisdn', t, MSISDN), ('msisdn', t, MSISDN)])     # also deduped in-batch
    again = db.session.query(TokenMap).one()
    assert again.created_at == created and again.ciphertext == cipher
    assert again.last_seen_at > seen


def test_empty_tokens_or_originals_are_skipped(ctx):
    assert token_store.remember_many([('msisdn', '', MSISDN), ('msisdn', tokenize(MSISDN), '')]) == 0
    assert db.session.query(TokenMap).count() == 0


def test_a_changed_secret_key_reports_undecryptable_instead_of_failing(ctx, monkeypatch):
    t = tokenize(MSISDN)
    token_store.remember_many([('msisdn', t, MSISDN)])
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', 'ee' * 32)
    got = token_store.reveal([t])
    assert got[t] == {'kind': 'msisdn', 'value': None, 'error': 'undecryptable'}


def test_outside_an_application_context_it_refuses(monkeypatch):
    with pytest.raises(token_store.TokenStoreError):
        token_store.remember_many([('msisdn', tokenize(MSISDN), MSISDN)])
    with pytest.raises(token_store.TokenStoreError):
        token_store.reveal([UNKNOWN])


def test_reveal_is_capped(ctx):
    with pytest.raises(ValueError):
        token_store.reveal([f'tk_msisdn_{i:032x}' for i in range(token_store.MAX_REVEAL + 1)])


def test_migration_matches_the_model(ctx):
    cols = {r[0]: (r[1], r[2]) for r in db.session.execute(text(
        "select column_name, data_type, is_nullable from information_schema.columns "
        "where table_name = 'ff_token_map'"))}
    assert set(cols) == {'id', 'token', 'kind', 'ciphertext', 'created_at', 'last_seen_at'}
    assert all(nullable == 'NO' for _, nullable in cols.values())
    uniq = db.session.execute(text(
        "select count(*) from pg_indexes where tablename = 'ff_token_map' and indexdef like '%UNIQUE%(token)%'")).scalar()
    assert uniq == 1


# -- retention ----------------------------------------------------------------------------

def _age(token, days):
    row = db.session.query(TokenMap).filter_by(token=token).one()
    row.last_seen_at = datetime.now(UTC) - timedelta(days=days)
    db.session.commit()


def test_purge_removes_only_mappings_not_seen_recently(ctx):
    old, new = tokenize(MSISDN), tokenize(OTHER)
    token_store.remember_many([('msisdn', old, MSISDN), ('msisdn', new, OTHER)])
    _age(old, 45)
    assert token_store.purge(30) == 1
    assert [r.token for r in db.session.query(TokenMap)] == [new]
    assert token_store.purge(0) == 1                      # 0 = everything
    assert db.session.query(TokenMap).count() == 0
    with pytest.raises(ValueError):
        token_store.purge(-1)


@pytest.mark.parametrize('raw,expected', [(None, 30), ('7', 7), ('0', 0), ('-5', 0), ('banana', 30), (' 12 ', 12)])
def test_retention_setting(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv('FLOWFORGE_TOKEN_MAP_RETENTION_DAYS', raising=False)
    else:
        monkeypatch.setenv('FLOWFORGE_TOKEN_MAP_RETENTION_DAYS', raw)
    assert token_store.retention_days() == expected


def test_daily_prune_job_honours_the_retention_window(app, ctx, monkeypatch):
    from flowforge.engine import scheduler
    old = tokenize(MSISDN)
    token_store.remember_many([('msisdn', old, MSISDN)])
    _age(old, 45)
    monkeypatch.setattr(scheduler, '_app', app)
    monkeypatch.setenv('FLOWFORGE_TOKEN_MAP_RETENTION_DAYS', '0')           # keep forever
    scheduler._prune_old_token_map()
    assert db.session.query(TokenMap).count() == 1
    monkeypatch.setenv('FLOWFORGE_TOKEN_MAP_RETENTION_DAYS', '30')
    scheduler._prune_old_token_map()
    db.session.expire_all()
    assert db.session.query(TokenMap).count() == 0


# -- the API --------------------------------------------------------------------------------

def _headers_for(app, client, role):
    name = f'tok_{role}_{uuid.uuid4().hex[:6]}'
    with app.app_context():
        db.session.add(User(username=name, role=role,
                            password_hash=bcrypt.hashpw(b'pw-for-test', bcrypt.gensalt(4)).decode()))
        db.session.commit()
    login = client.post('/api/auth/login', json={'username': name, 'password': 'pw-for-test'})
    assert login.status_code == 200, login.get_json()
    return name, {'Authorization': f'Bearer {login.get_json()["token"]}', 'Content-Type': 'application/json'}


def _drop_user(app, name):
    with app.app_context():
        u = db.session.query(User).filter_by(username=name).first()
        if u:
            db.session.delete(u)
            db.session.commit()


def _seed(app, *pairs):
    with app.app_context():
        token_store.remember_many([('msisdn', tokenize(v), v) for v in pairs])


def test_admin_can_reveal_and_it_is_audited_without_the_values(app, client, headers):
    _seed(app, MSISDN)
    t = tokenize(MSISDN)
    r = client.post('/api/tokens/reveal', headers=headers, json={'tokens': [t, UNKNOWN, t]})
    assert r.status_code == 200, r.get_json()
    assert r.headers['Cache-Control'] == 'no-store'
    assert r.get_json()['results'] == {t: {'kind': 'msisdn', 'value': MSISDN}, UNKNOWN: None}
    with app.app_context():
        row = (db.session.query(AuditLog).filter_by(action='TOKEN_REVEALED')
               .order_by(AuditLog.timestamp.desc()).first())
        assert row is not None
        assert row.details['requested'] == 2 and row.details['found'] == 1      # the duplicate was folded
        assert set(row.details['tokens']) == {t, UNKNOWN}
        assert MSISDN not in str(row.details) and MSISDN not in row.username


@pytest.mark.parametrize('role', ['editor', 'viewer'])
def test_only_admins_can_reveal(app, client, role):
    _seed(app, MSISDN)
    name, h = _headers_for(app, client, role)
    try:
        r = client.post('/api/tokens/reveal', headers=h, json={'tokens': [tokenize(MSISDN)]})
        assert r.status_code == 403
        assert MSISDN not in r.get_data(as_text=True)
    finally:
        _drop_user(app, name)


def test_reveal_needs_authentication(client):
    r = client.post('/api/tokens/reveal', json={'tokens': [UNKNOWN]})
    assert r.status_code == 401


@pytest.mark.parametrize('body', [
    None, {}, {'tokens': []}, {'tokens': 'tk_msisdn_' + '0' * 32}, {'tokens': [1, 2]},
    {'tokens': ['not-a-token']}, {'tokens': ['tk_msisdn_' + '0' * 32, "x'; drop table ff_token_map; --"]},
    {'tokens': ['tk_msisdn_' + 'Z' * 32]},
])
def test_malformed_requests_are_rejected(client, headers, body):
    r = client.post('/api/tokens/reveal', headers=headers, json=body)
    assert r.status_code == 400


def test_too_many_tokens_are_rejected(client, headers):
    tokens = [f'tk_msisdn_{i:032x}' for i in range(token_store.MAX_REVEAL + 1)]
    assert client.post('/api/tokens/reveal', headers=headers, json={'tokens': tokens}).status_code == 400


# -- reconcile ------------------------------------------------------------------------------

class FakeConn:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute_query_with_columns_chunked(self, sql, params=(), chunk_size=5000):
        return ['k'], iter(self.rows)


def _step(config, left, right):
    cfg = {'left_connection_id': 'L', 'right_connection_id': 'R', 'left_query': 'SELECT k FROM l',
           'right_query': 'SELECT k FROM r', 'sample_size': 50, **config}
    step = ReconcileStep('recon', cfg)
    conns = {'L': left, 'R': right}
    step._open = lambda cid: FakeConn(conns[cid])
    return step


LEFT = [(f'1555000{i:04d}',) for i in range(30)]
RIGHT = [(f'1555000{i:04d}',) for i in range(10, 40)]


def test_reconcile_stores_the_sampled_mappings_and_they_can_be_revealed(app):
    with app.app_context():
        r = _step({'tokenize_keys': True, 'token_store': True}, LEFT, RIGHT).run({'steps': {}})
        assert r.success, r.error
        assert r.output_variables['recon_token_store_ok'] is True and 'Token mappings: ok' in r.logs
        shown = {row['key'] for row in r.rows}
        assert len(shown) == 20                               # 10 only-left + 10 only-right
        assert db.session.query(TokenMap).count() == 20
        revealed = token_store.reveal(sorted(shown))
        originals = {v['value'] for v in revealed.values()}
        assert originals == {k for (k,) in LEFT[:10]} | {k for (k,) in RIGHT[-10:]}
        assert not any('1555000' in str(row) for row in r.rows)               # the result itself stays tokenized


def test_only_the_capped_sample_is_stored_not_every_key(app):
    with app.app_context():
        r = _step({'tokenize_keys': True, 'token_store': True, 'sample_size': 4}, LEFT, RIGHT).run({'steps': {}})
        assert r.success and r.output_variables['recon_discrepancies'] == 20
        assert db.session.query(TokenMap).count() == 8        # 4 per category x 2 categories


def test_store_is_off_unless_asked(app):
    with app.app_context():
        r = _step({'tokenize_keys': True}, LEFT, RIGHT).run({'steps': {}})
        assert r.success and 'recon_token_store_ok' not in r.output_variables
        assert db.session.query(TokenMap).count() == 0


def test_token_store_requires_tokenize_keys(app):
    with app.app_context():
        r = _step({'token_store': True}, LEFT, RIGHT).run({'steps': {}})
        assert not r.success and 'tokenize_keys' in r.error
        assert db.session.query(TokenMap).count() == 0


def test_a_failing_store_does_not_lose_the_audit_result(app):
    with app.app_context(), patch.object(token_store, 'remember_many', side_effect=RuntimeError('db down')):
        r = _step({'tokenize_keys': True, 'token_store': True}, LEFT, RIGHT).run({'steps': {}})
    assert r.success and r.output_variables['recon_discrepancies'] == 20      # findings intact
    assert r.output_variables['recon_token_store_ok'] is False
    assert 'failed' in r.logs and 'db down' in r.logs
    assert all(row['key'].startswith('tk_') for row in r.rows)                # and still no raw keys


def test_partitioned_passes_store_every_sampled_key_once(app):
    with app.app_context():
        r = _step({'tokenize_keys': True, 'token_store': True, 'partitions': 4}, LEFT, RIGHT).run({'steps': {}})
        assert r.success and db.session.query(TokenMap).count() == 20


# -- CLI ------------------------------------------------------------------------------------

def test_cli_find_prints_the_same_token_the_step_would():
    from flowforge.cli import cli
    out = CliRunner().invoke(cli, ['tokens', 'find', MSISDN, '+1 (555) 000-1234'])
    assert out.exit_code == 0, out.output
    lines = [ln.split('\t') for ln in out.output.strip().splitlines()]
    assert [t for _, t in lines] == [tokenize(MSISDN), tokenize(MSISDN)]      # formatting does not change the token


def test_cli_find_fails_cleanly_without_a_key(monkeypatch):
    from flowforge.cli import cli
    monkeypatch.delenv('FLOWFORGE_SECRET_KEY')
    monkeypatch.delenv('FLOWFORGE_TOKEN_KEY', raising=False)
    out = CliRunner().invoke(cli, ['tokens', 'find', MSISDN])
    assert out.exit_code == 1 and 'key' in out.output.lower()
    assert MSISDN not in out.output.replace(f'{MSISDN}\t', '')


@pytest.mark.parametrize('args', [[], ['--all', '--older-than-days', '5']])
def test_cli_purge_needs_exactly_one_scope(args):
    from flowforge.cli import cli
    out = CliRunner().invoke(cli, ['tokens', 'purge', '--yes', *args])
    assert out.exit_code == 2 and 'exactly one' in out.output
