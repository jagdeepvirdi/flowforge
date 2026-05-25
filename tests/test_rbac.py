"""MU-3 spot-check: viewer gets 403 on write routes, 200 on reads.
Admin/editor tokens must still pass on all routes.
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures: viewer and editor tokens
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def viewer_headers(client, auth_token):
    """Create a viewer user once for the session and return its auth headers."""
    admin_hdrs = {'Authorization': f'Bearer {auth_token}', 'Content-Type': 'application/json'}
    client.post('/api/users', json={'username': 'rbac_viewer', 'password': 'Pass1234!', 'role': 'viewer'},
                headers=admin_hdrs)
    resp = client.post('/api/auth/login', json={'username': 'rbac_viewer', 'password': 'Pass1234!'})
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture(scope='session')
def editor_headers(client, auth_token):
    """Create an editor user once for the session and return its auth headers."""
    admin_hdrs = {'Authorization': f'Bearer {auth_token}', 'Content-Type': 'application/json'}
    client.post('/api/users', json={'username': 'rbac_editor', 'password': 'Pass1234!', 'role': 'editor'},
                headers=admin_hdrs)
    resp = client.post('/api/auth/login', json={'username': 'rbac_editor', 'password': 'Pass1234!'})
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------

def test_viewer_can_read_pipelines(client, viewer_headers):
    assert client.get('/api/pipelines', headers=viewer_headers).status_code == 200


def test_viewer_cannot_create_pipeline(client, viewer_headers):
    resp = client.post('/api/pipelines', json={'name': 'viewer-pipe'}, headers=viewer_headers)
    assert resp.status_code == 403


def test_editor_can_create_pipeline(client, editor_headers):
    resp = client.post('/api/pipelines', json={'name': 'editor-pipe'}, headers=editor_headers)
    assert resp.status_code in (200, 201)


def test_viewer_cannot_run_pipeline(client, viewer_headers, auth_token):
    admin_hdrs = {'Authorization': f'Bearer {auth_token}', 'Content-Type': 'application/json'}
    create = client.post('/api/pipelines', json={'name': 'rbac-run-test'}, headers=admin_hdrs)
    pid = create.get_json()['id']
    resp = client.post(f'/api/pipelines/{pid}/run', headers=viewer_headers)
    assert resp.status_code == 403


def test_viewer_cannot_delete_pipeline(client, viewer_headers, auth_token):
    admin_hdrs = {'Authorization': f'Bearer {auth_token}', 'Content-Type': 'application/json'}
    create = client.post('/api/pipelines', json={'name': 'rbac-delete-test'}, headers=admin_hdrs)
    pid = create.get_json()['id']
    assert client.delete(f'/api/pipelines/{pid}', headers=viewer_headers).status_code == 403


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def test_viewer_can_read_reports(client, viewer_headers):
    assert client.get('/api/report-configs', headers=viewer_headers).status_code == 200


def test_viewer_cannot_create_report(client, viewer_headers):
    resp = client.post('/api/report-configs',
                       json={'name': 'r', 'query': 'SELECT 1', 'format': 'csv',
                             'output_filename': 'r.csv'},
                       headers=viewer_headers)
    assert resp.status_code == 403


def test_editor_can_create_report(client, editor_headers):
    resp = client.post('/api/report-configs',
                       json={'name': 'editor-report', 'query': 'SELECT 1', 'format': 'csv',
                             'output_filename': 'r.csv'},
                       headers=editor_headers)
    assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Email configs
# ---------------------------------------------------------------------------

def test_viewer_can_read_email_configs(client, viewer_headers):
    assert client.get('/api/email-configs', headers=viewer_headers).status_code == 200


def test_viewer_cannot_create_email_config(client, viewer_headers):
    resp = client.post('/api/email-configs',
                       json={'name': 'e', 'subject': 's', 'body_template': 'b'},
                       headers=viewer_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Recipients
# ---------------------------------------------------------------------------

def test_viewer_can_read_recipient_groups(client, viewer_headers):
    assert client.get('/api/recipient-groups', headers=viewer_headers).status_code == 200


def test_viewer_cannot_create_recipient_group(client, viewer_headers):
    resp = client.post('/api/recipient-groups',
                       json={'name': 'g', 'addresses': ['a@b.com']},
                       headers=viewer_headers)
    assert resp.status_code == 403


def test_editor_can_create_recipient_group(client, editor_headers):
    resp = client.post('/api/recipient-groups',
                       json={'name': 'rbac-editor-group', 'addresses': ['x@y.com']},
                       headers=editor_headers)
    assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Connections (admin-only writes)
# ---------------------------------------------------------------------------

def test_viewer_can_read_connections(client, viewer_headers):
    assert client.get('/api/db-connections', headers=viewer_headers).status_code == 200


def test_editor_cannot_create_connection(client, editor_headers):
    resp = client.post('/api/db-connections',
                       json={'name': 'c', 'db_type': 'postgresql',
                             'config': {'host': 'localhost', 'port': 5432,
                                        'database': 'x', 'username': 'u', 'password': 'p'}},
                       headers=editor_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Providers (admin-only writes)
# ---------------------------------------------------------------------------

def test_viewer_can_read_providers(client, viewer_headers):
    assert client.get('/api/email-providers', headers=viewer_headers).status_code == 200


def test_editor_cannot_create_provider(client, editor_headers):
    resp = client.post('/api/email-providers',
                       json={'name': 'p', 'provider_type': 'smtp',
                             'config': {'host': 'smtp.example.com', 'port': 587,
                                        'username': 'u', 'password': 'p'}},
                       headers=editor_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Runs (cancel)
# ---------------------------------------------------------------------------

def test_viewer_cannot_cancel_run(client, viewer_headers):
    # Non-existent run — 403 must come before 404
    resp = client.post('/api/runs/00000000-0000-0000-0000-000000000001/cancel',
                       headers=viewer_headers)
    assert resp.status_code == 403


def test_cancel_nonexistent_run_returns_404(client, headers):
    resp = client.post('/api/runs/00000000-0000-0000-0000-000000000001/cancel',
                       headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Users (admin-only)
# ---------------------------------------------------------------------------

def test_viewer_cannot_list_users(client, viewer_headers):
    assert client.get('/api/users', headers=viewer_headers).status_code == 403


def test_editor_cannot_create_user(client, editor_headers):
    resp = client.post('/api/users',
                       json={'username': 'mu3_newuser', 'password': 'Pass1234!', 'role': 'viewer'},
                       headers=editor_headers)
    assert resp.status_code == 403
