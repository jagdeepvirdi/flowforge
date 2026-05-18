"""Tests for email config CRUD (/api/email-configs)."""
import pytest


EMAIL_PAYLOAD = {
    'name': 'Test Email Config',
    'description': 'Automated test',
    'subject': 'Monthly Report - {{ current_month }}',
    'body_template': '<p>Hello {{ pipeline_name }}</p>',
    'to_addresses': ['recipient@example.com'],
    'cc_addresses': [],
    'bcc_addresses': [],
    'attachment_max_mb': 10,
}


@pytest.fixture
def email_id(client, headers):
    resp = client.post('/api/email-configs', json=EMAIL_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    eid = resp.get_json()['id']
    yield eid
    client.delete(f'/api/email-configs/{eid}', headers=headers)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_list_email_configs(client, headers):
    resp = client.get('/api/email-configs', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_email_config(client, headers):
    resp = client.post('/api/email-configs', json=EMAIL_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Email Config'
    assert data['subject'] == EMAIL_PAYLOAD['subject']
    assert 'id' in data
    client.delete(f'/api/email-configs/{data["id"]}', headers=headers)


def test_create_email_config_missing_name(client, headers):
    bad = {**EMAIL_PAYLOAD}
    del bad['name']
    resp = client.post('/api/email-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_email_config_missing_subject(client, headers):
    bad = {**EMAIL_PAYLOAD}
    del bad['subject']
    resp = client.post('/api/email-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_email_config_missing_body(client, headers):
    bad = {**EMAIL_PAYLOAD}
    del bad['body_template']
    resp = client.post('/api/email-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_get_email_config(client, headers, email_id):
    resp = client.get(f'/api/email-configs/{email_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == email_id
    assert data['to_addresses'] == ['recipient@example.com']


def test_update_email_config(client, headers, email_id):
    resp = client.put(f'/api/email-configs/{email_id}',
                      json={'name': 'Updated Config', 'attachment_max_mb': 25},
                      headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Updated Config'
    assert data['attachment_max_mb'] == 25


def test_update_recipients(client, headers, email_id):
    new_recipients = ['a@example.com', 'b@example.com']
    resp = client.put(f'/api/email-configs/{email_id}',
                      json={'to_addresses': new_recipients}, headers=headers)
    assert resp.status_code == 200
    assert set(resp.get_json()['to_addresses']) == set(new_recipients)


def test_delete_email_config(client, headers):
    resp = client.post('/api/email-configs', json=EMAIL_PAYLOAD, headers=headers)
    eid = resp.get_json()['id']
    assert client.delete(f'/api/email-configs/{eid}', headers=headers).status_code == 200
    assert client.get(f'/api/email-configs/{eid}', headers=headers).status_code == 404


def test_get_nonexistent_email_config(client, headers):
    resp = client.get('/api/email-configs/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404
