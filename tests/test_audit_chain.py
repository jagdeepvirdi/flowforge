"""Tamper-resistant audit log: the maintenance trigger and the keyed hash chain.

The attacker these tests play is someone with owner-level SQL who can open the maintenance gate (or
drop the trigger): prevention does not stop them, detection must.
"""
import threading
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from flowforge import audit, audit_chain
from flowforge.db.models import AuditLog, db

KEY_A = 'aa' * 32


@pytest.fixture(autouse=True)
def _clean(app):
    _owner(app, 'TRUNCATE ff_audit_log')
    yield
    _owner(app, 'TRUNCATE ff_audit_log')


def _owner(app, sql, **params):
    """Run SQL the way a table owner who knows about the gate would."""
    with app.app_context(), db.engine.begin() as conn:
        conn.execute(text("SELECT set_config('flowforge.audit_maintenance', 'on', true)"))
        return conn.execute(text(sql), params)


def _write(app, n=5, user='alice', user_id=None, ip='10.0.0.1'):
    with app.app_context():
        for i in range(n):
            audit._write_db_audit('TEST_ACTION', user, user_id, ip, {'i': i, 'who': user})


def _append_at(app, ts, user='alice', user_id=None, n=1):
    with app.app_context(), db.engine.begin() as conn:
        for i in range(n):
            audit_chain.append(conn, 'TEST_ACTION', user, user_id, '', {'i': i}, ts=ts)


def _verify(app, anchor=None):
    with app.app_context(), db.engine.connect() as conn:
        return audit_chain.verify(conn, anchor=anchor)


def _rows(app):
    with app.app_context():
        return db.session.execute(text(
            'SELECT seq, action, username, anonymized, prev_hash, row_hash FROM ff_audit_log '
            'WHERE seq IS NOT NULL ORDER BY seq')).all()


# -- the chain ------------------------------------------------------------------------------

def test_writes_form_one_verifiable_chain(app):
    _write(app, 10)
    rep = _verify(app)
    assert rep.ok, rep.problems
    assert (rep.chained_rows, rep.first_seq, rep.last_seq, rep.legacy_rows) == (10, 1, 10, 0)
    rows = _rows(app)
    assert rows[0].prev_hash == audit_chain.GENESIS
    assert all(b.prev_hash == a.row_hash for a, b in zip(rows, rows[1:], strict=False))
    assert rep.tail == f'10:{rows[-1].row_hash}'


def test_concurrent_writers_still_produce_one_gapless_chain(app):
    def worker(name):
        for _ in range(15):
            with app.app_context():
                audit._write_db_audit('TEST_ACTION', name, None, '', {})

    threads = [threading.Thread(target=worker, args=(f'user{i}',)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    rep = _verify(app)
    assert rep.ok, rep.problems
    assert rep.chained_rows == 60 and rep.first_seq == 1 and rep.last_seq == 60


def test_each_write_logs_its_chain_position_as_an_anchor(app, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger='flowforge.audit'):
        audit.logging.getLogger('flowforge.audit').propagate = True
        _write(app, 1)
    rows = _rows(app)
    assert any(f'seq=1  hash={rows[0].row_hash}' in rec.getMessage() for rec in caplog.records)


# -- prevention: the trigger -----------------------------------------------------------------

@pytest.mark.parametrize('sql', [
    "UPDATE ff_audit_log SET username = 'mallory'",
    'DELETE FROM ff_audit_log',
    'TRUNCATE ff_audit_log',
])
def test_the_application_cannot_modify_audit_rows(app, sql):
    _write(app, 3)
    with app.app_context(), pytest.raises(DBAPIError) as e, db.engine.begin() as conn:
        conn.execute(text(sql))
    assert 'append-only' in str(e.value)
    assert len(_rows(app)) == 3


def test_the_orm_cannot_edit_or_delete_either(app):
    _write(app, 2)
    with app.app_context():
        with pytest.raises(DBAPIError):
            db.session.query(AuditLog).delete()
        db.session.rollback()
        with pytest.raises(DBAPIError):
            db.session.query(AuditLog).update({'username': 'x'})
        db.session.rollback()
    assert len(_rows(app)) == 2


def test_inserts_are_still_allowed(app):
    _write(app, 1)
    assert len(_rows(app)) == 1


def test_the_migration_installed_the_guard(app):
    with app.app_context():
        trig = {r[0] for r in db.session.execute(text(
            "select tgname from pg_trigger where tgrelid = 'ff_audit_log'::regclass and not tgisinternal"))}
        cols = {r[0] for r in db.session.execute(text(
            "select column_name from information_schema.columns where table_name = 'ff_audit_log'"))}
    assert {'ff_audit_log_no_modify', 'ff_audit_log_no_truncate'} <= trig
    assert {'seq', 'prev_hash', 'content_digest', 'row_hash', 'anonymized'} <= cols


# -- detection: an owner who bypasses the gate -------------------------------------------------

@pytest.mark.parametrize('sql,what', [
    ("UPDATE ff_audit_log SET username = 'mallory' WHERE seq = 5", 'username'),
    ("UPDATE ff_audit_log SET action = 'NOTHING_TO_SEE' WHERE seq = 5", 'action'),
    ("UPDATE ff_audit_log SET details = '{\"i\": 99}' WHERE seq = 5", 'details'),
    ("UPDATE ff_audit_log SET ip_address = '6.6.6.6' WHERE seq = 5", 'ip'),
    ("UPDATE ff_audit_log SET timestamp = timestamp - interval '1 day' WHERE seq = 5", 'timestamp'),
])
def test_an_edited_row_is_detected(app, sql, what):
    _write(app, 10)
    assert _verify(app).ok
    _owner(app, sql)
    rep = _verify(app)
    assert not rep.ok and any('seq 5' in p for p in rep.problems), (what, rep.problems)


def test_an_edited_row_cannot_be_repaired_without_the_key(app):
    """Recomputing the content digest (plain SHA-256, public) is not enough: row_hash is an HMAC."""
    _write(app, 6)
    with app.app_context():
        row = db.session.execute(text('SELECT * FROM ff_audit_log WHERE seq = 3')).one()
        forged = audit_chain.content_digest(3, row.timestamp, row.action, 'mallory', None, row.ip_address,
                                            row.details)
    _owner(app, "UPDATE ff_audit_log SET username = 'mallory', content_digest = :d WHERE seq = 3", d=forged)
    rep = _verify(app)
    assert not rep.ok and any('row_hash does not match' in p and 'seq 3' in p for p in rep.problems)


def test_a_deleted_middle_row_is_detected(app):
    _write(app, 10)
    _owner(app, 'DELETE FROM ff_audit_log WHERE seq = 6')
    rep = _verify(app)
    assert not rep.ok and any('missing or duplicated between seq 5 and 7' in p for p in rep.problems)


def test_a_forged_row_without_the_key_is_detected(app):
    _write(app, 4)
    tail = _rows(app)[-1]
    with app.app_context():
        digest = audit_chain.content_digest(5, datetime.now(UTC), 'LOGIN_SUCCESS', 'admin', None, '', {})
    _owner(app, "INSERT INTO ff_audit_log (id, timestamp, action, username, ip_address, details, seq, prev_hash,"
                " content_digest, row_hash) VALUES (:id, now(), 'LOGIN_SUCCESS', 'admin', '', '{}', 5, :p, :d, :h)",
           id=str(uuid.uuid4()), p=tail.row_hash, d=digest, h='f' * 64)
    rep = _verify(app)
    assert not rep.ok and any('seq 5' in p for p in rep.problems)


def test_removing_the_newest_rows_is_only_caught_with_an_anchor(app):
    """The honest limit: nothing inside the table says how long the chain should be."""
    _write(app, 8)
    anchor = _verify(app).tail
    _owner(app, 'DELETE FROM ff_audit_log WHERE seq > 5')
    assert _verify(app).ok                                         # a clean, shorter chain
    rep = _verify(app, anchor=anchor)
    assert not rep.ok and any('newest rows were removed' in p for p in rep.problems)


def test_an_anchor_catches_a_rewritten_row_and_passes_on_an_intact_chain(app):
    _write(app, 5)
    anchor = _verify(app).tail
    good = _verify(app, anchor=anchor)
    assert good.ok and good.anchor_checked
    _write(app, 3)                                                 # growing the chain keeps the anchor valid
    assert _verify(app, anchor=anchor).ok
    seq = anchor.split(':')[0]
    bad = f'{seq}:{"0" * 64}'
    rep = _verify(app, anchor=bad)
    assert not rep.ok and any('its hash differs' in p for p in rep.problems)


def test_a_malformed_anchor_is_a_usage_error_not_a_pass(app):
    _write(app, 1)
    with pytest.raises(ValueError):
        _verify(app, anchor='not-an-anchor')


def test_unchained_rows_after_the_chain_started_are_flagged_but_legacy_rows_are_not(app):
    old = datetime.now(UTC) - timedelta(days=400)
    _owner(app, "INSERT INTO ff_audit_log (id, timestamp, action, username, details) "
                "VALUES (:id, :t, 'OLD_EVENT', 'legacy', '{}')", id=str(uuid.uuid4()), t=old)
    _write(app, 3)
    rep = _verify(app)
    assert rep.ok and rep.legacy_rows == 1 and any('predate the chain' in n for n in rep.notes)
    _owner(app, "INSERT INTO ff_audit_log (id, timestamp, action, username, details) "
                "VALUES (:id, now(), 'SNEAKY', 'x', '{}')", id=str(uuid.uuid4()))
    rep = _verify(app)
    assert not rep.ok and rep.unchained_after_start == 1


# -- keys ------------------------------------------------------------------------------------

def test_without_a_key_the_event_is_still_recorded_but_flagged_as_unchained(app, monkeypatch):
    _write(app, 2)
    monkeypatch.delenv('FLOWFORGE_SECRET_KEY')
    monkeypatch.delenv('FLOWFORGE_AUDIT_CHAIN_KEY', raising=False)
    _write(app, 1)
    monkeypatch.undo()
    with app.app_context():
        assert db.session.execute(text('select count(*) from ff_audit_log')).scalar() == 3
    rep = _verify(app)
    assert not rep.ok and rep.unchained_after_start == 1


def test_verify_without_a_key_says_so_instead_of_passing(app, monkeypatch):
    _write(app, 2)
    monkeypatch.delenv('FLOWFORGE_SECRET_KEY')
    monkeypatch.delenv('FLOWFORGE_AUDIT_CHAIN_KEY', raising=False)
    rep = _verify(app)
    assert not rep.ok and 'cannot verify' in rep.problems[0]


def test_rotating_the_secret_key_breaks_the_chain_unless_a_chain_key_is_pinned(app, monkeypatch):
    _write(app, 4)
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', 'ee' * 32)
    rep = _verify(app)
    assert not rep.ok and any('wrong key' in p for p in rep.problems)
    monkeypatch.undo()
    _owner(app, 'TRUNCATE ff_audit_log')
    monkeypatch.setenv('FLOWFORGE_AUDIT_CHAIN_KEY', KEY_A)
    _write(app, 4)
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', 'ee' * 32)
    assert _verify(app).ok                                           # pinned key survives the rotation


@pytest.mark.parametrize('bad', ['zz', 'ab' * 8])
def test_a_bad_chain_key_is_rejected(monkeypatch, bad):
    monkeypatch.setenv('FLOWFORGE_AUDIT_CHAIN_KEY', bad)
    with pytest.raises(audit_chain.ChainKeyError):
        audit_chain.chain_key()


# -- retention -------------------------------------------------------------------------------

def _prune(app, days=30):
    with app.app_context():
        n = audit_chain.prune(db.session.connection(), datetime.now(UTC) - timedelta(days=days))
        db.session.commit()
        return n


def test_prune_removes_old_rows_and_leaves_a_verifiable_checkpoint(app):
    _append_at(app, datetime.now(UTC) - timedelta(days=60), n=6)
    _append_at(app, datetime.now(UTC) - timedelta(days=1), n=4)
    assert _prune(app) == 6
    rep = _verify(app)
    assert rep.ok, rep.problems
    rows = _rows(app)
    assert rows[0].seq == 7 and rows[-1].action == audit_chain.PRUNED
    with app.app_context():
        d = db.session.execute(text("select details from ff_audit_log where action = 'AUDIT_PRUNED'")).scalar()
    assert d['through_seq'] == 6 and d['deleted'] == 6


def test_prune_does_nothing_and_adds_no_checkpoint_when_nothing_is_old(app):
    _append_at(app, datetime.now(UTC) - timedelta(days=1), n=3)
    assert _prune(app) == 0
    assert [r.action for r in _rows(app)] == ['TEST_ACTION'] * 3


def test_prune_can_remove_every_old_row_and_repeat(app):
    _append_at(app, datetime.now(UTC) - timedelta(days=90), n=5)
    assert _prune(app) == 5
    assert [r.action for r in _rows(app)] == [audit_chain.PRUNED] and _verify(app).ok
    _append_at(app, datetime.now(UTC) - timedelta(days=45), n=3)       # old again; the first checkpoint is old too
    _prune(app)
    rep = _verify(app)
    assert rep.ok, rep.problems
    _write(app, 2)
    assert _verify(app).ok


def test_deleting_the_head_without_a_checkpoint_is_detected(app):
    _write(app, 10)
    _owner(app, 'DELETE FROM ff_audit_log WHERE seq <= 4')
    rep = _verify(app)
    assert not rep.ok and any('no retention checkpoint' in p for p in rep.problems)


def test_a_forged_checkpoint_does_not_excuse_a_deleted_head(app):
    """The checkpoint row is itself sealed, so an attacker without the key cannot add one."""
    _write(app, 10)
    tail = _rows(app)[-1]
    _owner(app, 'DELETE FROM ff_audit_log WHERE seq <= 4')
    with app.app_context():
        digest = audit_chain.content_digest(11, datetime.now(UTC), audit_chain.PRUNED, 'system', None, '',
                                            {'through_seq': 4, 'through_hash': 'x', 'deleted': 4,
                                             'anonymized_removed': 0})
    _owner(app, "INSERT INTO ff_audit_log (id, timestamp, action, username, ip_address, details, seq, prev_hash,"
                " content_digest, row_hash) VALUES (:id, now(), 'AUDIT_PRUNED', 'system', '',"
                " '{\"through_seq\": 4}', 11, :p, :d, :h)",
           id=str(uuid.uuid4()), p=tail.row_hash, d=digest, h='a' * 64)
    assert not _verify(app).ok


def test_prune_also_clears_old_legacy_rows(app):
    _owner(app, "INSERT INTO ff_audit_log (id, timestamp, action, username, details) VALUES "
                "(:a, now() - interval '90 days', 'OLD', 'u', '{}'), (:b, now() - interval '1 day', 'NEWISH', 'u', '{}')",
           a=str(uuid.uuid4()), b=str(uuid.uuid4()))
    assert _prune(app) == 1
    with app.app_context():
        assert [r[0] for r in db.session.execute(text('select action from ff_audit_log'))] == ['NEWISH']


def test_the_scheduler_job_prunes_through_the_chain(app, monkeypatch):
    from flowforge.engine import scheduler
    _append_at(app, datetime.now(UTC) - timedelta(days=200), n=4)
    _append_at(app, datetime.now(UTC) - timedelta(days=1), n=2)
    monkeypatch.setattr(scheduler, '_app', app)
    monkeypatch.setenv('FLOWFORGE_AUDIT_RETENTION_DAYS', '30')
    scheduler._prune_old_audit_logs()
    rep = _verify(app)
    assert rep.ok, rep.problems
    assert [r.action for r in _rows(app)][-1] == audit_chain.PRUNED and _rows(app)[0].seq == 5


def test_a_failed_prune_leaves_the_log_untouched(app, monkeypatch):
    _append_at(app, datetime.now(UTC) - timedelta(days=60), n=3)
    monkeypatch.delenv('FLOWFORGE_SECRET_KEY')
    monkeypatch.delenv('FLOWFORGE_AUDIT_CHAIN_KEY', raising=False)
    with app.app_context(), pytest.raises(audit_chain.ChainKeyError):
        audit_chain.prune(db.session.connection(), datetime.now(UTC))
    monkeypatch.undo()
    assert len(_rows(app)) == 3                                      # no key, no checkpoint, so nothing deleted


# -- GDPR purge ------------------------------------------------------------------------------

def _purge(app, uid, name):
    with app.app_context():
        n = audit_chain.anonymize_actor(db.session.connection(), uid, name, f'[deleted:{uid[:8]}]')
        db.session.commit()
        return n


def test_gdpr_purge_keeps_the_chain_valid_and_records_how_many_rows_it_touched(app):
    uid = str(uuid.uuid4())
    _write(app, 3, user='bob', user_id=uid, ip='9.9.9.9')
    _write(app, 4, user='carol')
    assert _purge(app, uid, 'bob') == 3
    rep = _verify(app)
    assert rep.ok, rep.problems
    assert rep.anonymized_rows == 3
    with app.app_context():
        mine = db.session.execute(text("select username, user_id, ip_address from ff_audit_log "
                                       "where username like '[deleted:%'")).all()
        event = db.session.execute(text("select details from ff_audit_log where action = 'AUDIT_ANONYMIZED'")).scalar()
    assert len(mine) == 3 and all(r.user_id is None and r.ip_address is None for r in mine)
    assert event['rows'] == 3
    assert _purge(app, uid, 'bob') == 0                              # idempotent
    assert _verify(app).ok


def test_flagging_a_row_as_anonymized_to_hide_an_edit_is_detected(app):
    uid = str(uuid.uuid4())
    _write(app, 2, user='bob', user_id=uid)
    _write(app, 4, user='carol')
    _purge(app, uid, 'bob')
    _owner(app, "UPDATE ff_audit_log SET username = 'mallory', anonymized = TRUE WHERE seq = 5")   # was carol's row
    rep = _verify(app)
    assert not rep.ok and any('flagged anonymized' in p for p in rep.problems)


def test_unflagging_an_anonymized_row_is_detected(app):
    uid = str(uuid.uuid4())
    _write(app, 3, user='bob', user_id=uid)
    _purge(app, uid, 'bob')
    _owner(app, 'UPDATE ff_audit_log SET anonymized = FALSE WHERE seq = 2')
    rep = _verify(app)
    assert not rep.ok and any('seq 2' in p for p in rep.problems)


def test_pruning_anonymized_rows_keeps_the_accounting_balanced(app):
    uid = str(uuid.uuid4())
    _append_at(app, datetime.now(UTC) - timedelta(days=60), user='bob', user_id=uid, n=3)
    _append_at(app, datetime.now(UTC) - timedelta(days=60), user='carol', n=2)
    _append_at(app, datetime.now(UTC) - timedelta(days=1), user='carol', n=2)
    _purge(app, uid, 'bob')
    assert _verify(app).ok
    _prune(app)                                                      # removes the old rows, bob's among them
    rep = _verify(app)
    assert rep.ok, rep.problems


def test_user_admin_purge_goes_through_the_chain(app):
    import bcrypt

    from flowforge.db.models import User
    from flowforge.user_admin import delete_user
    name = f'purge_{uuid.uuid4().hex[:6]}'
    with app.app_context():
        u = User(username=name, role='viewer', password_hash=bcrypt.hashpw(b'pw', bcrypt.gensalt(4)).decode())
        db.session.add(u)
        db.session.commit()
        uid = u.id
    _write(app, 3, user=name, user_id=uid)
    with app.app_context():
        assert delete_user(name, purge=True)
    rep = _verify(app)
    assert rep.ok, rep.problems
    assert rep.anonymized_rows == 3


def test_api_purge_goes_through_the_chain(app, client, headers):
    import bcrypt

    from flowforge.db.models import User
    name = f'apipurge_{uuid.uuid4().hex[:6]}'
    with app.app_context():
        u = User(username=name, role='viewer', password_hash=bcrypt.hashpw(b'pw', bcrypt.gensalt(4)).decode())
        db.session.add(u)
        db.session.commit()
        uid = u.id
    _write(app, 2, user=name, user_id=uid)
    r = client.delete(f'/api/users/{uid}?purge=true', headers=headers)
    assert r.status_code == 200, r.get_json()
    rep = _verify(app)
    assert rep.ok, rep.problems
    assert rep.anonymized_rows == 2


# -- API and CLI ------------------------------------------------------------------------------

def test_verify_endpoint_reports_ok_and_tampering(app, client, headers):
    _write(app, 5)
    ok = client.get('/api/audit-logs/verify', headers=headers)
    assert ok.status_code == 200 and ok.get_json()['ok'] is True and ok.get_json()['chained_rows'] >= 5
    _owner(app, "UPDATE ff_audit_log SET username = 'mallory' WHERE seq = 2")
    bad = client.get('/api/audit-logs/verify', headers=headers)
    assert bad.status_code == 200 and bad.get_json()['ok'] is False
    assert any('seq 2' in p for p in bad.get_json()['problems'])


def test_verify_endpoint_validates_the_anchor_and_is_admin_only(app, client, headers):
    _write(app, 2)
    bad = client.get('/api/audit-logs/verify?anchor=nope-secret-marker', headers=headers)
    assert bad.status_code == 400
    assert 'seq' in bad.get_json()['error'] and 'nope-secret-marker' not in bad.get_data(as_text=True)   # fixed text, no echo
    assert client.get('/api/audit-logs/verify').status_code == 401


def test_cli_verify_and_anchor(app):
    from flowforge.cli import cli
    _write(app, 4)
    with patch('flowforge.cli._create_app', return_value=app):
        anchor = CliRunner().invoke(cli, ['audit', 'anchor'])
        assert anchor.exit_code == 0 and anchor.output.strip().startswith('4:')
        good = CliRunner().invoke(cli, ['audit', 'verify', '--anchor', anchor.output.strip()])
        assert good.exit_code == 0 and good.output.startswith('OK')
        _owner(app, "UPDATE ff_audit_log SET username = 'mallory' WHERE seq = 3")
        bad = CliRunner().invoke(cli, ['audit', 'verify'])
        assert bad.exit_code == 1 and 'FAILED' in bad.output
        usage = CliRunner().invoke(cli, ['audit', 'verify', '--anchor', 'garbage'])
        assert usage.exit_code == 2
