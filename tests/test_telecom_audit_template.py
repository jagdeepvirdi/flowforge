"""The orphaned-subscription audit template (examples/telecom-orphaned-subscriptions.yaml).

Three layers:
* structure: the YAML parses, every reconcile config is accepted by the step, the alert
  condition is valid and fires/stays quiet on the right counts;
* import: the file goes through the real ``/api/pipelines/import`` path;
* live: the template's own SQL is run against PostgreSQL seeded with the synthetic dataset
  and must find exactly the planted anomalies (and none of the in-flight subscribers).
  Skipped unless FLOWFORGE_DB_URL points at a database whose name contains "test".
"""
import copy
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
import yaml

from flowforge.demo.telecom import generate, seed_postgres
from flowforge.engine.context import evaluate_condition, validate_condition
from flowforge.steps.reconcile import ReconcileStep
from flowforge.tokenization import tokenize

TEMPLATE = Path(__file__).resolve().parent.parent / 'examples' / 'telecom-orphaned-subscriptions.yaml'


@pytest.fixture(scope='module')
def doc():
    return yaml.safe_load(TEMPLATE.read_text(encoding='utf-8'))


@pytest.fixture(autouse=True)
def _token_key(monkeypatch):
    # tokenization needs a key; use the environment's if present, else a throwaway one
    if not (os.environ.get('FLOWFORGE_SECRET_KEY') or os.environ.get('FLOWFORGE_TOKEN_KEY')):
        monkeypatch.setenv('FLOWFORGE_SECRET_KEY', 'cd' * 32)


def _step(doc, name):
    return next(s for s in doc['steps'] if s['name'] == name)


def _vars(doc):
    return {v['var_key']: v['var_value'] for v in doc['variables']}


# -- structure ----------------------------------------------------------------------------

def test_template_is_disabled_and_has_expected_shape(doc):
    assert doc['enabled'] is False          # never starts running on import
    assert [s['step_type'] for s in doc['steps']] == ['reconcile', 'reconcile', 'email']
    assert [s['step_order'] for s in doc['steps']] == [1, 2, 3]
    assert len({s['name'] for s in doc['steps']}) == 3


def test_reconcile_configs_are_accepted_by_the_step(doc):
    prefixes = []
    for s in doc['steps']:
        if s['step_type'] != 'reconcile':
            continue
        cfg = ReconcileStep(s['name'], s['config'])._parse_config()
        prefixes.append(cfg['prefix'])
    assert len(set(prefixes)) == 2, 'output prefixes must differ or the steps overwrite each other'


def test_alert_condition_is_valid_and_thresholded(doc):
    expr = _step(doc, 'send_alert')['config']['run_if']
    assert validate_condition(expr) is None
    v = _vars(doc)

    def ctx(billing, hlr):
        return {**v, 'steps': {'audit_crm_vs_billing': {'rows_affected': billing},
                               'audit_crm_vs_hlr': {'rows_affected': hlr}}}

    assert evaluate_condition(expr, ctx(60, 41)) is True       # 101 > 100
    assert evaluate_condition(expr, ctx(60, 40)) is False      # 100 is not > 100
    assert evaluate_condition(expr, ctx(0, 0)) is False


def test_samples_are_tokenized_by_default(doc):
    for s in doc['steps']:
        if s['step_type'] == 'reconcile':
            assert s['config']['tokenize_keys'] is True, f"{s['name']} would emit raw MSISDNs"


def test_no_secret_variables_and_no_credentials_in_template(doc):
    assert not any(v.get('is_secret') for v in doc['variables'])
    text = TEMPLATE.read_text(encoding='utf-8').lower()
    assert 'password' not in text.replace('user:pass', '')


# -- import through the API ---------------------------------------------------------------

def test_template_imports_through_the_api(client, headers):
    resp = client.post('/api/pipelines/import',
                       json={'yaml_content': TEMPLATE.read_text(encoding='utf-8')}, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    p = resp.get_json()
    try:
        assert p['enabled'] is False
        assert len(p['steps']) == 3
        alert = next(s for s in p['steps'] if s['name'] == 'send_alert')
        assert 'run_if' in alert['config']
    finally:
        client.delete(f'/api/pipelines/{p["id"]}', headers=headers)


# -- live PostgreSQL ----------------------------------------------------------------------

class _PgConn:
    """Minimal stand-in for a FlowForge connection backed by a real psycopg2 connection."""

    def __init__(self, dsn):
        import psycopg2
        self._c = psycopg2.connect(dsn)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._c.close()
        return False

    def execute_query_with_columns_chunked(self, sql, params=(), chunk_size=5000):
        with self._c.cursor() as cur:
            cur.execute(sql)
            return [d[0] for d in cur.description], iter(cur.fetchall())


@pytest.fixture(scope='module')
def seeded_dsn():
    url = os.environ.get('FLOWFORGE_DB_URL', '')
    if 'test' not in urlparse(url).path.lower():
        pytest.skip('live audit test needs FLOWFORGE_DB_URL pointing at a *test* database')
    try:
        ds = generate(2000, orphan_rate=0.02, in_flight_rate=0.01, seed=11, now=datetime.now(UTC))
        seed_postgres(url, ds)
    except Exception as e:  # database not reachable
        pytest.skip(f'PostgreSQL not available: {e}')
    return url, ds.truth


def _run(doc, name, dsn):
    cfg = copy.deepcopy(_step(doc, name)['config'])
    cfg['sample_size'] = 1000          # large enough to return every planted key
    for side in ('left', 'right'):
        cfg[f'{side}_connection_id'] = 'pg'
    context = {**_vars(doc), 'steps': {}}
    with patch.object(ReconcileStep, '_open', lambda self, cid: _PgConn(dsn)):
        return ReconcileStep(name, cfg).run(context)


def _keys(result, issue):
    return {r['key'] for r in result.rows if r['issue'] == issue}


def _tok(msisdns):
    # the template tokenizes sampled keys, so ground truth is compared as tokens
    return {tokenize(m) for m in msisdns}


def test_live_billing_audit_finds_exactly_the_planted_anomalies(doc, seeded_dsn):
    dsn, truth = seeded_dsn
    r = _run(doc, 'audit_crm_vs_billing', dsn)
    assert r.success, r.error
    assert _keys(r, 'only_in_left') == _tok(truth.keys['active_unbilled'])
    assert _keys(r, 'value_mismatch') == _tok(truth.keys['charge_mismatch'])
    assert _keys(r, 'only_in_right') == set()
    assert not (_tok(truth.keys['in_flight']) & {row['key'] for row in r.rows})
    assert not any(m in repr(r.rows) for m in truth.keys['active_unbilled'])


def test_live_hlr_audit_finds_exactly_the_planted_anomalies(doc, seeded_dsn):
    dsn, truth = seeded_dsn
    r = _run(doc, 'audit_crm_vs_hlr', dsn)
    assert r.success, r.error
    assert _keys(r, 'only_in_left') == _tok(truth.keys['billed_unprovisioned'])
    assert _keys(r, 'only_in_right') == _tok(truth.keys['status_mismatch'])
    assert not (_tok(truth.keys['in_flight']) & {row['key'] for row in r.rows})
    assert not any(m in repr(r.rows) for m in truth.keys['active_unbilled'])
