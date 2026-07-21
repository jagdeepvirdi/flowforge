"""Tests for GET /api/registry/<category> and GET /api/registry (ARCH-9/ARCH-11)."""
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_plugins():
    from flowforge.engine.loader import _reset_plugin_state_for_tests
    _reset_plugin_state_for_tests()
    yield
    _reset_plugin_state_for_tests()


# ── GET /api/registry/<category> ────────────────────────────────────────────────

def test_steps_category(client, headers):
    resp = client.get('/api/registry/steps', headers=headers)
    assert resp.status_code == 200
    rows = resp.get_json()
    keys = {r['key'] for r in rows}
    assert 'db_procedure' in keys
    row = next(r for r in rows if r['key'] == 'db_procedure')
    assert row['plugin'] is False
    assert row['installed'] is True
    assert row['requires'] is None


def test_connections_category(client, headers):
    resp = client.get('/api/registry/connections', headers=headers)
    assert resp.status_code == 200
    rows = {r['key']: r for r in resp.get_json()}
    assert set(rows) == {
        'bigquery', 'mssql', 'mysql', 'odbc', 'oracle', 'postgresql', 'redshift', 'snowflake',
    }
    assert rows['postgresql']['plugin'] is False
    assert rows['postgresql']['display_name'] == 'PostgreSQL'
    assert rows['postgresql']['requires'] is None
    assert rows['postgresql']['installed'] is True
    assert rows['oracle']['requires'] == 'oracle'
    assert rows['oracle']['tier'] is None


def test_email_providers_category(client, headers):
    resp = client.get('/api/registry/email_providers', headers=headers)
    assert resp.status_code == 200
    rows = {r['key']: r for r in resp.get_json()}
    assert set(rows) == {'gmail', 'mailgun', 'microsoft365', 'sendgrid', 'ses', 'smtp'}
    assert rows['smtp']['display_name'] == 'SMTP'
    assert rows['ses']['requires'] == 'ses'


def test_unknown_category_returns_404(client, headers):
    resp = client.get('/api/registry/bogus', headers=headers)
    assert resp.status_code == 404
    assert 'Unknown registry category' in resp.get_json()['error']


def test_requires_auth(client):
    resp = client.get('/api/registry/steps')
    assert resp.status_code == 401


def test_installed_false_when_module_missing(client, headers):
    resp = client.get('/api/registry/connections', headers=headers)
    rows = {r['key']: r for r in resp.get_json()}
    with patch('importlib.util.find_spec', return_value=None):
        resp2 = client.get('/api/registry/connections', headers=headers)
    rows2 = {r['key']: r for r in resp2.get_json()}
    # oracledb is installed in this dev venv, so it flips from installed to not
    assert rows['oracle']['installed'] is True
    assert rows2['oracle']['installed'] is False


def test_plugin_connection_reflected_in_registry(client, headers, monkeypatch, tmp_path):
    (tmp_path / 'my_conn_plugin.py').write_text("""
from flowforge.connections.base import BaseConnection

class MyConnection(BaseConnection):
    db_type = 'my_custom_db'

    @classmethod
    def from_config(cls, cfg):
        return cls()

    def execute_procedure(self, name, params): pass
    def execute_query(self, sql, params=()): return []
    def execute_query_with_columns(self, sql, params=()): return [], []
    def execute_write(self, sql, params=()): return 0
    def execute_many(self, sql, rows): return 0
    def make_placeholders(self, n): return ''
    def test(self): return True, 0
    def close(self): pass
""")
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _load_plugins
    _load_plugins()

    resp = client.get('/api/registry/connections', headers=headers)
    rows = {r['key']: r for r in resp.get_json()}
    assert rows['my_custom_db']['plugin'] is True
    assert rows['my_custom_db']['installed'] is True
    assert rows['my_custom_db']['requires'] is None


# ── GET /api/registry (aggregate) ───────────────────────────────────────────────

def test_aggregate_registry_covers_all_categories(client, headers):
    resp = client.get('/api/registry', headers=headers)
    assert resp.status_code == 200
    rows = resp.get_json()
    categories = {r['category'] for r in rows}
    assert categories == {'steps', 'connections', 'email_providers'}


def test_aggregate_registry_entitled_always_true(client, headers):
    resp = client.get('/api/registry', headers=headers)
    rows = resp.get_json()
    assert all(r['entitled'] is True for r in rows)


def test_aggregate_registry_entry_shape(client, headers):
    resp = client.get('/api/registry', headers=headers)
    rows = resp.get_json()
    pg = next(r for r in rows if r['category'] == 'connections' and r['key'] == 'postgresql')
    assert pg == {
        'category': 'connections', 'key': 'postgresql', 'display_name': 'PostgreSQL',
        'description': '', 'requires': None, 'tier': None, 'plugin': False,
        'installed': True, 'entitled': True,
    }


def test_aggregate_registry_requires_auth(client):
    resp = client.get('/api/registry')
    assert resp.status_code == 401
