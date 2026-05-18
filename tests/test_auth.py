"""Tests for JWT authentication endpoints."""


def test_health(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'


def test_login_success(client):
    resp = client.post('/api/auth/login', json={'username': 'testadmin', 'password': 'testpass'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'token' in data
    assert len(data['token']) > 20


def test_login_wrong_password(client):
    resp = client.post('/api/auth/login', json={'username': 'testadmin', 'password': 'wrongpass'})
    assert resp.status_code == 401
    assert 'error' in resp.get_json()


def test_login_unknown_user(client):
    resp = client.post('/api/auth/login', json={'username': 'nobody', 'password': 'pass'})
    assert resp.status_code == 401


def test_login_missing_fields(client):
    resp = client.post('/api/auth/login', json={})
    assert resp.status_code == 400


def test_protected_route_no_token(client):
    resp = client.get('/api/pipelines')
    assert resp.status_code == 401


def test_protected_route_bad_token(client):
    resp = client.get('/api/pipelines', headers={'Authorization': 'Bearer notavalidtoken'})
    assert resp.status_code == 401


def test_protected_route_valid_token(client, headers):
    resp = client.get('/api/pipelines', headers=headers)
    assert resp.status_code == 200
