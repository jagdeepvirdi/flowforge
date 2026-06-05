"""Tests for JWT token validation edge cases."""
from datetime import UTC, datetime, timedelta


def _make_token(app, username='testadmin', expiry_delta=timedelta(hours=1), secret=None):
    import jwt
    payload = {
        'sub': username,
        'iat': datetime.now(UTC),
        'exp': datetime.now(UTC) + expiry_delta,
    }
    key = secret or app.config['SECRET_KEY']
    return jwt.encode(payload, key, algorithm='HS256')


def test_valid_token_accepted(app, client, headers):
    resp = client.get('/api/pipelines', headers=headers)
    assert resp.status_code == 200


def test_expired_token_rejected(app, client):
    token = _make_token(app, expiry_delta=timedelta(seconds=-1))
    resp = client.get('/api/pipelines', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 401


def test_wrong_secret_rejected(app, client):
    token = _make_token(app, secret='wrong' * 10)
    resp = client.get('/api/pipelines', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 401


def test_malformed_token_rejected(client):
    resp = client.get('/api/pipelines', headers={'Authorization': 'Bearer not.a.jwt'})
    assert resp.status_code == 401


def test_empty_bearer_rejected(client):
    resp = client.get('/api/pipelines', headers={'Authorization': 'Bearer '})
    assert resp.status_code == 401


def test_no_authorization_header_rejected(client):
    resp = client.get('/api/pipelines')
    assert resp.status_code == 401


def test_wrong_scheme_rejected(client, auth_token):
    resp = client.get('/api/pipelines', headers={'Authorization': f'Basic {auth_token}'})
    assert resp.status_code == 401


def test_verify_token_valid(app):
    class _FakeUser:
        id = 'test-verify-id'
        username = 'testadmin'
        role = 'admin'

    with app.app_context():
        from flowforge.api.auth import generate_token, verify_token
        token = generate_token(_FakeUser())
        payload = verify_token(token)
        assert payload is not None and payload.get('sub') == 'testadmin'


def test_verify_token_expired(app):
    with app.app_context():
        from flowforge.api.auth import verify_token
        token = _make_token(app, expiry_delta=timedelta(seconds=-1))
        assert verify_token(token) is None


def test_verify_token_bad_secret(app):
    with app.app_context():
        from flowforge.api.auth import verify_token
        token = _make_token(app, secret='badsecret' * 5)
        assert verify_token(token) is None
