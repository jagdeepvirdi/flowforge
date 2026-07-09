"""Tests for GET/PUT /api/settings/retention.

Resets the ff_system_settings singleton row back to all-defaults after every
test in this module, since it's process-wide state that other test modules
(e.g. test_setup_extended.py's retention assertions) also depend on.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_retention_settings(client, headers):
    yield
    client.put('/api/settings/retention', json={
        'run_retention_days': None, 'audit_retention_days': None, 'output_ttl_days': None,
    }, headers=headers)


# ── GET /settings/retention ───────────────────────────────────────────────────

def test_get_requires_auth(client):
    resp = client.get('/api/settings/retention')
    assert resp.status_code == 401


def test_get_returns_expected_keys(client, headers):
    resp = client.get('/api/settings/retention', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) == {'run_retention_days', 'audit_retention_days', 'output_ttl_days', 'is_custom'}
    assert set(data['is_custom'].keys()) == {'run_retention_days', 'audit_retention_days', 'output_ttl_days'}


def test_get_defaults_are_not_custom(client, headers):
    resp = client.get('/api/settings/retention', headers=headers)
    data = resp.get_json()
    assert data['is_custom'] == {
        'run_retention_days': False, 'audit_retention_days': False, 'output_ttl_days': False,
    }


def test_get_reflects_env_var_defaults(client, headers, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_RUN_RETENTION_DAYS', '45')
    monkeypatch.delenv('FLOWFORGE_AUDIT_RETENTION_DAYS', raising=False)
    monkeypatch.setenv('FLOWFORGE_OUTPUT_TTL_DAYS', '3')
    resp = client.get('/api/settings/retention', headers=headers)
    data = resp.get_json()
    assert data['run_retention_days'] == 45
    assert data['audit_retention_days'] == 45  # falls back to run retention
    assert data['output_ttl_days'] == 3


# ── PUT /settings/retention — auth/role gating ────────────────────────────────

def test_put_requires_auth(client):
    resp = client.put('/api/settings/retention', json={'run_retention_days': 30})
    assert resp.status_code == 401


# ── PUT /settings/retention — happy path ──────────────────────────────────────

def test_put_updates_and_persists(client, headers):
    resp = client.put('/api/settings/retention', json={'run_retention_days': 45}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['run_retention_days'] == 45

    follow_up = client.get('/api/settings/retention', headers=headers)
    data = follow_up.get_json()
    assert data['run_retention_days'] == 45
    assert data['is_custom']['run_retention_days'] is True
    # Untouched fields stay at their (non-custom) defaults
    assert data['is_custom']['audit_retention_days'] is False


def test_put_can_update_multiple_fields_at_once(client, headers):
    resp = client.put('/api/settings/retention', json={
        'run_retention_days': 10, 'audit_retention_days': 20, 'output_ttl_days': 3,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {'run_retention_days': 10, 'audit_retention_days': 20, 'output_ttl_days': 3}


def test_put_zero_is_allowed_for_run_and_audit_retention(client, headers):
    resp = client.put('/api/settings/retention', json={
        'run_retention_days': 0, 'audit_retention_days': 0,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['run_retention_days'] == 0
    assert data['audit_retention_days'] == 0


def test_put_null_resets_field_to_default(client, headers):
    client.put('/api/settings/retention', json={'run_retention_days': 45}, headers=headers)
    resp = client.put('/api/settings/retention', json={'run_retention_days': None}, headers=headers)
    assert resp.status_code == 200
    follow_up = client.get('/api/settings/retention', headers=headers)
    assert follow_up.get_json()['is_custom']['run_retention_days'] is False


def test_put_sets_updated_by(client, headers, app):
    client.put('/api/settings/retention', json={'run_retention_days': 15}, headers=headers)
    from flowforge.db.models import SystemSettings, db
    with app.app_context():
        row = db.session.get(SystemSettings, 1)
        assert row is not None
        assert row.updated_by == 'testadmin'


def test_put_writes_audit_log_entry(client, headers, app):
    from flowforge.db.models import AuditLog, db
    with app.app_context():
        before = db.session.query(AuditLog).filter_by(action='SETTINGS_UPDATED').count()
    client.put('/api/settings/retention', json={'run_retention_days': 22}, headers=headers)
    with app.app_context():
        after = db.session.query(AuditLog).filter_by(action='SETTINGS_UPDATED').count()
    assert after == before + 1


# ── PUT /settings/retention — validation ──────────────────────────────────────

def test_put_output_ttl_zero_is_rejected(client, headers):
    resp = client.put('/api/settings/retention', json={'output_ttl_days': 0}, headers=headers)
    assert resp.status_code == 400
    assert 'output_ttl_days' in resp.get_json()['error']


def test_put_output_ttl_negative_is_rejected(client, headers):
    resp = client.put('/api/settings/retention', json={'output_ttl_days': -5}, headers=headers)
    assert resp.status_code == 400


def test_put_run_retention_negative_is_rejected(client, headers):
    resp = client.put('/api/settings/retention', json={'run_retention_days': -1}, headers=headers)
    assert resp.status_code == 400


def test_put_non_integer_value_is_rejected(client, headers):
    resp = client.put('/api/settings/retention', json={'run_retention_days': 'thirty'}, headers=headers)
    assert resp.status_code == 400


def test_put_boolean_value_is_rejected(client, headers):
    resp = client.put('/api/settings/retention', json={'run_retention_days': True}, headers=headers)
    assert resp.status_code == 400


def test_put_unknown_field_is_rejected(client, headers):
    resp = client.put('/api/settings/retention', json={'bogus_field': 5}, headers=headers)
    assert resp.status_code == 400
    assert 'bogus_field' in resp.get_json()['error']


def test_put_empty_body_is_rejected(client, headers):
    resp = client.put('/api/settings/retention', json={}, headers=headers)
    assert resp.status_code == 400
