"""Extended tests for /api/email-providers — covers the previously-uncovered
routes: PUT 404, DELETE 404, is_default update, and the /test endpoint
(lines 75, 81, 99, 110-118 of providers.py).
"""
from unittest.mock import MagicMock, patch

import pytest

SMTP_PAYLOAD = {
    'name': 'Ext SMTP',
    'provider_type': 'smtp',
    'config': {
        'host': 'smtp.example.com',
        'port': 587,
        'username': 'u@example.com',
        'password': 'secret',
        'use_tls': True,
    },
}

MISSING_UUID = '00000000-0000-0000-0000-000000000000'


@pytest.fixture
def provider_id(client, headers):
    resp = client.post('/api/email-providers', json=SMTP_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/email-providers/{pid}', headers=headers)


# ── PUT 404 (line 75) ─────────────────────────────────────────────────────────

def test_update_nonexistent_provider_returns_404(client, headers):
    resp = client.put(
        f'/api/email-providers/{MISSING_UUID}',
        json={'name': 'Ghost'},
        headers=headers,
    )
    assert resp.status_code == 404


# ── is_default update (line 81) ───────────────────────────────────────────────

def test_update_is_default_field(client, headers, provider_id):
    resp = client.put(
        f'/api/email-providers/{provider_id}',
        json={'is_default': True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()['is_default'] is True


def test_update_is_default_false(client, headers, provider_id):
    client.put(f'/api/email-providers/{provider_id}',
               json={'is_default': True}, headers=headers)
    resp = client.put(f'/api/email-providers/{provider_id}',
                      json={'is_default': False}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['is_default'] is False


# ── DELETE 404 (line 99) ──────────────────────────────────────────────────────

def test_delete_nonexistent_provider_returns_404(client, headers):
    resp = client.delete(f'/api/email-providers/{MISSING_UUID}', headers=headers)
    assert resp.status_code == 404


# ── /test endpoint (lines 110-118) ────────────────────────────────────────────

def test_test_provider_success(client, headers, provider_id):
    mock_provider = MagicMock()
    mock_provider.test.return_value = (True, 'Connected to smtp.example.com:587')
    with patch('flowforge.email_providers.factory.get_email_provider', return_value=mock_provider):
        resp = client.post(f'/api/email-providers/{provider_id}/test', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_test_provider_failure(client, headers, provider_id):
    mock_provider = MagicMock()
    mock_provider.test.return_value = (False, 'Authentication failed')
    with patch('flowforge.email_providers.factory.get_email_provider', return_value=mock_provider):
        resp = client.post(f'/api/email-providers/{provider_id}/test', headers=headers)
    assert resp.status_code == 502
    data = resp.get_json()
    assert data['success'] is False
    assert 'Authentication failed' in data['error']


def test_test_provider_exception(client, headers, provider_id):
    with patch('flowforge.email_providers.factory.get_email_provider',
               side_effect=ValueError('Provider not found')):
        resp = client.post(f'/api/email-providers/{provider_id}/test', headers=headers)
    assert resp.status_code == 502
    data = resp.get_json()
    assert data['success'] is False
    assert 'ValueError' in data['error']
