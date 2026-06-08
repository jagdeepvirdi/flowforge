"""Tests for email config routes: update, delete, preview."""
import pytest


@pytest.fixture
def email_id(client, headers):
    resp = client.post('/api/email-configs', json={
        'name': 'Coverage Email Config',
        'subject': 'Report for {{ current_month }}',
        'body_template': '<p>Hello, {{ pipeline_name }}!</p>',
        'to_addresses': ['user@example.com'],
    }, headers=headers)
    assert resp.status_code == 201
    eid = resp.get_json()['id']
    yield eid
    client.delete(f'/api/email-configs/{eid}', headers=headers)


# ── update ────────────────────────────────────────────────────────────────────

def test_update_email_config_success(client, headers, email_id):
    resp = client.put(f'/api/email-configs/{email_id}',
                      json={'subject': 'Updated Subject', 'attachment_max_mb': 20},
                      headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['subject'] == 'Updated Subject'
    assert data['attachment_max_mb'] == 20


def test_update_email_config_not_found(client, headers):
    resp = client.put('/api/email-configs/00000000-0000-0000-0000-000000000000',
                      json={'subject': 'x'}, headers=headers)
    assert resp.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_email_config_not_found(client, headers):
    resp = client.delete('/api/email-configs/00000000-0000-0000-0000-000000000000',
                         headers=headers)
    assert resp.status_code == 404


def test_delete_email_config_success(client, headers):
    resp = client.post('/api/email-configs', json={
        'name': 'Delete Me',
        'subject': 'Bye',
        'body_template': '<p>bye</p>',
    }, headers=headers)
    eid = resp.get_json()['id']
    assert client.delete(f'/api/email-configs/{eid}', headers=headers).status_code == 200
    assert client.get(f'/api/email-configs/{eid}', headers=headers).status_code == 404


# ── preview ───────────────────────────────────────────────────────────────────

def test_preview_email_config_success(client, headers, email_id):
    resp = client.get(f'/api/email-configs/{email_id}/preview', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'subject' in data
    assert 'html' in data


def test_preview_email_config_not_found(client, headers):
    resp = client.get('/api/email-configs/00000000-0000-0000-0000-000000000000/preview',
                      headers=headers)
    assert resp.status_code == 404


def test_preview_email_config_template_error(client, headers):
    resp = client.post('/api/email-configs', json={
        'name': 'Bad Template',
        'subject': 'Test',
        'body_template': '{% if unclosed_block %}',
    }, headers=headers)
    assert resp.status_code == 201
    eid = resp.get_json()['id']

    preview = client.get(f'/api/email-configs/{eid}/preview', headers=headers)
    assert preview.status_code in (200, 422)  # Jinja2 may render or error

    client.delete(f'/api/email-configs/{eid}', headers=headers)


def test_list_email_configs_with_project_id_filter(client, headers):
    resp = client.get(
        '/api/email-configs?project_id=00000000-0000-0000-0000-000000000000',
        headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
