"""Tests for user management API (MU-2): POST/GET/PATCH/DELETE /api/users
and POST /api/auth/change-password."""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(client, headers, username='mu2_worker', password='Pass1234!', role='editor'):
    resp = client.post('/api/users', json={'username': username, 'password': password, 'role': role},
                       headers=headers)
    return resp


def _token_for(client, username, password='Pass1234!'):
    resp = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.get_json()}"
    return resp.get_json()['token']


def _viewer_headers(client, headers):
    """Create a temporary viewer user and return its auth headers."""
    uname = 'mu2_viewer_temp'
    _create_user(client, headers, username=uname, role='viewer')
    token = _token_for(client, uname)
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


# ---------------------------------------------------------------------------
# GET /api/users
# ---------------------------------------------------------------------------

def test_list_users_admin(client, headers):
    resp = client.get('/api/users', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert any(u['username'] == 'testadmin' for u in data)


def test_list_users_requires_admin(client, headers):
    viewer_hdrs = _viewer_headers(client, headers)
    resp = client.get('/api/users', headers=viewer_hdrs)
    assert resp.status_code == 403


def test_list_users_requires_auth(client):
    resp = client.get('/api/users')
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/users
# ---------------------------------------------------------------------------

def test_create_user_success(client, headers):
    resp = _create_user(client, headers, username='mu2_create_ok')
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['username'] == 'mu2_create_ok'
    assert data['role'] == 'editor'
    assert 'id' in data and data['id']
    assert 'password_hash' not in data


def test_create_user_all_roles(client, headers):
    for role in ('admin', 'editor', 'viewer'):
        resp = _create_user(client, headers, username=f'mu2_role_{role}', role=role)
        assert resp.status_code == 201, f"Failed for role={role}: {resp.get_json()}"
        assert resp.get_json()['role'] == role


def test_create_user_invalid_role(client, headers):
    resp = _create_user(client, headers, username='mu2_badrole', role='superuser')
    assert resp.status_code == 400


def test_create_user_missing_fields(client, headers):
    resp = client.post('/api/users', json={'username': 'mu2_nopw'}, headers=headers)
    assert resp.status_code == 400


def test_create_user_duplicate_username(client, headers):
    _create_user(client, headers, username='mu2_dup')
    resp = _create_user(client, headers, username='mu2_dup')
    assert resp.status_code == 409


def test_create_user_requires_admin(client, headers):
    viewer_hdrs = _viewer_headers(client, headers)
    resp = client.post('/api/users',
                       json={'username': 'mu2_viewer_create', 'password': 'Pass1234!', 'role': 'viewer'},
                       headers=viewer_hdrs)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/users/{id}
# ---------------------------------------------------------------------------

def test_update_user_role(client, headers):
    create_resp = _create_user(client, headers, username='mu2_patch_role')
    uid = create_resp.get_json()['id']

    resp = client.patch(f'/api/users/{uid}', json={'role': 'viewer'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['role'] == 'viewer'


def test_update_user_username(client, headers):
    create_resp = _create_user(client, headers, username='mu2_patch_name_before')
    uid = create_resp.get_json()['id']

    resp = client.patch(f'/api/users/{uid}', json={'username': 'mu2_patch_name_after'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['username'] == 'mu2_patch_name_after'


def test_update_user_cannot_demote_self(client, headers, auth_token):
    # Get the current admin's own id
    me = client.get('/api/auth/me', headers=headers).get_json()
    uid = me['id']

    resp = client.patch(f'/api/users/{uid}', json={'role': 'viewer'}, headers=headers)
    assert resp.status_code == 403
    assert 'demote' in resp.get_json()['error'].lower()


def test_update_user_not_found(client, headers):
    resp = client.patch('/api/users/00000000-0000-0000-0000-000000000099',
                        json={'role': 'viewer'}, headers=headers)
    assert resp.status_code == 404


def test_update_user_requires_admin(client, headers):
    create_resp = _create_user(client, headers, username='mu2_patch_victim')
    uid = create_resp.get_json()['id']
    viewer_hdrs = _viewer_headers(client, headers)
    resp = client.patch(f'/api/users/{uid}', json={'role': 'admin'}, headers=viewer_hdrs)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/users/{id}
# ---------------------------------------------------------------------------

def test_delete_user_success(client, headers):
    create_resp = _create_user(client, headers, username='mu2_delete_me')
    uid = create_resp.get_json()['id']

    resp = client.delete(f'/api/users/{uid}', headers=headers)
    assert resp.status_code == 200
    assert 'deleted' in resp.get_json()['message']


def test_delete_user_cannot_delete_self(client, headers):
    me = client.get('/api/auth/me', headers=headers).get_json()
    uid = me['id']

    resp = client.delete(f'/api/users/{uid}', headers=headers)
    assert resp.status_code == 403


def test_delete_user_not_found(client, headers):
    resp = client.delete('/api/users/00000000-0000-0000-0000-000000000099', headers=headers)
    assert resp.status_code == 404


def test_delete_user_requires_admin(client, headers):
    create_resp = _create_user(client, headers, username='mu2_del_victim2')
    uid = create_resp.get_json()['id']
    viewer_hdrs = _viewer_headers(client, headers)
    resp = client.delete(f'/api/users/{uid}', headers=viewer_hdrs)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/auth/change-password
# ---------------------------------------------------------------------------

def test_change_password_success(client, headers):
    _create_user(client, headers, username='mu2_chpw', password='OldPass1!')
    token = _token_for(client, 'mu2_chpw', 'OldPass1!')
    hdrs = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    resp = client.post('/api/auth/change-password',
                       json={'current_password': 'OldPass1!', 'new_password': 'NewPass2@'},
                       headers=hdrs)
    assert resp.status_code == 200

    # Old password should no longer work
    assert client.post('/api/auth/login',
                       json={'username': 'mu2_chpw', 'password': 'OldPass1!'}).status_code == 401
    # New password should work
    assert client.post('/api/auth/login',
                       json={'username': 'mu2_chpw', 'password': 'NewPass2@'}).status_code == 200


def test_change_password_wrong_current(client, headers):
    _create_user(client, headers, username='mu2_chpw_wrong', password='OldPass1!')
    token = _token_for(client, 'mu2_chpw_wrong', 'OldPass1!')
    hdrs = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    resp = client.post('/api/auth/change-password',
                       json={'current_password': 'wrongpass', 'new_password': 'NewPass2@'},
                       headers=hdrs)
    assert resp.status_code == 401


def test_change_password_too_short(client, headers):
    _create_user(client, headers, username='mu2_chpw_short', password='OldPass1!')
    token = _token_for(client, 'mu2_chpw_short', 'OldPass1!')
    hdrs = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    resp = client.post('/api/auth/change-password',
                       json={'current_password': 'OldPass1!', 'new_password': 'short'},
                       headers=hdrs)
    assert resp.status_code == 400


def test_change_password_requires_auth(client):
    resp = client.post('/api/auth/change-password',
                       json={'current_password': 'a', 'new_password': 'b'})
    assert resp.status_code == 401
