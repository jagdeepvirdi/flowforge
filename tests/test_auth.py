"""Tests for JWT authentication endpoints and token revocation (NEW-4)."""
import pytest


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


# ── Token revocation / logout (NEW-4) ─────────────────────────────────────────

def test_logout_requires_auth(client):
    resp = client.post('/api/auth/logout')
    assert resp.status_code == 401


def test_logout_with_bad_token_rejected(client):
    resp = client.post('/api/auth/logout',
                       headers={'Authorization': 'Bearer bad.token.value'})
    assert resp.status_code == 401


def test_logout_success(app, client):
    """Logging out with a valid token should return 200 and write jti to blocklist."""
    # Get a fresh token (not the shared session token — we're revoking it)
    login_resp = client.post('/api/auth/login',
                             json={'username': 'testadmin', 'password': 'testpass'})
    assert login_resp.status_code == 200
    token = login_resp.get_json()['token']

    logout_resp = client.post('/api/auth/logout',
                              headers={'Authorization': f'Bearer {token}'})
    assert logout_resp.status_code == 200
    assert 'message' in logout_resp.get_json()


def test_revoked_token_rejected_on_protected_route(app, client):
    """After logout the same token must be denied on any protected endpoint."""
    login_resp = client.post('/api/auth/login',
                             json={'username': 'testadmin', 'password': 'testpass'})
    token = login_resp.get_json()['token']

    client.post('/api/auth/logout',
                headers={'Authorization': f'Bearer {token}'})

    # Same token used again should now be blocked
    resp = client.get('/api/pipelines',
                      headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 401


def test_revoke_token_unit(app):
    """revoke_token() should blocklist the jti and verify_token() should return None."""
    with app.app_context():
        from flowforge.api.auth import generate_token, revoke_token, verify_token
        token = generate_token('testadmin')
        assert verify_token(token) == 'testadmin'
        username = revoke_token(token)
        assert username == 'testadmin'
        assert verify_token(token) is None


def test_generate_token_has_jti(app):
    """Tokens issued after NEW-4 must carry a non-empty jti claim."""
    import jwt as _jwt
    with app.app_context():
        from flowforge.api.auth import generate_token
        token = generate_token('testadmin')
        payload = _jwt.decode(
            token,
            app.config.get('JWT_SECRET') or app.config['SECRET_KEY'],
            algorithms=['HS256'],
        )
        assert 'jti' in payload
        assert payload['jti']  # non-empty string


def test_revoke_token_without_jti_returns_username(app):
    """Legacy tokens (no jti) are not blocklisted but revoke_token still returns the sub."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone
    with app.app_context():
        from flowforge.api.auth import revoke_token
        secret = app.config.get('JWT_SECRET') or app.config['SECRET_KEY']
        # Craft a token with no jti (simulates pre-NEW-4 tokens)
        payload = {
            'sub': 'testadmin',
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = _jwt.encode(payload, secret, algorithm='HS256')
        username = revoke_token(token)
        assert username == 'testadmin'
