"""Tests for auth.py branches: MFA token generation/verification, require_role."""
from datetime import UTC, datetime, timedelta


# ── generate_mfa_token / verify_mfa_token ─────────────────────────────────────

def test_generate_mfa_token_has_mfa_step_claim(app):
    import jwt as _jwt

    class _User:
        id = 'mfa-test-id'
        username = 'testadmin'
        role = 'admin'

    with app.app_context():
        from flowforge.api.auth import generate_mfa_token
        token = generate_mfa_token(_User())
        secret = app.config.get('JWT_SECRET') or app.config['SECRET_KEY']
        payload = _jwt.decode(token, secret, algorithms=['HS256'])
        assert payload.get('mfa_step') is True
        assert payload['sub'] == 'testadmin'


def test_verify_mfa_token_returns_payload_for_valid_token(app):
    class _User:
        id = 'mfa-verify-id'
        username = 'testadmin'
        role = 'admin'

    with app.app_context():
        from flowforge.api.auth import generate_mfa_token, verify_mfa_token
        token = generate_mfa_token(_User())
        payload = verify_mfa_token(token)
        assert payload is not None
        assert payload['sub'] == 'testadmin'
        assert payload['mfa_step'] is True


def test_verify_mfa_token_rejects_regular_token(app):
    class _User:
        id = 'mfa-regular-id'
        username = 'testadmin'
        role = 'admin'

    with app.app_context():
        from flowforge.api.auth import generate_token, verify_mfa_token
        token = generate_token(_User())
        # Regular token has no mfa_step — must be rejected
        assert verify_mfa_token(token) is None


def test_verify_mfa_token_rejects_invalid_token(app):
    with app.app_context():
        from flowforge.api.auth import verify_mfa_token
        assert verify_mfa_token('not.a.valid.token') is None


def test_verify_mfa_token_rejects_revoked_token(app):
    class _User:
        id = 'mfa-revoke-id'
        username = 'testadmin'
        role = 'admin'

    with app.app_context():
        from flowforge.api.auth import generate_mfa_token, revoke_token, verify_mfa_token
        token = generate_mfa_token(_User())
        assert verify_mfa_token(token) is not None
        revoke_token(token)
        assert verify_mfa_token(token) is None


# ── verify_token rejects MFA-step tokens ──────────────────────────────────────

def test_verify_token_rejects_mfa_step_token(app):
    class _User:
        id = 'verify-mfa-id'
        username = 'testadmin'
        role = 'admin'

    with app.app_context():
        from flowforge.api.auth import generate_mfa_token, verify_token
        mfa_token = generate_mfa_token(_User())
        # MFA challenge tokens must NOT be usable as session tokens
        assert verify_token(mfa_token) is None


# ── require_role ──────────────────────────────────────────────────────────────

def test_require_role_allows_admin(client, headers):
    # admin can access editor-only endpoints
    resp = client.post('/api/pipelines', json={'name': 'Role Test Pipeline'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    client.delete(f'/api/pipelines/{pid}', headers=headers)


def test_require_role_blocks_viewer(app, client):
    """A viewer-role token must be rejected on editor-only endpoints."""
    import bcrypt

    with app.app_context():
        from flowforge.db.models import User, db
        viewer = User(
            username='viewer_role_test',
            password_hash=bcrypt.hashpw(b'viewpass', bcrypt.gensalt(4)).decode(),
            role='viewer',
        )
        db.session.add(viewer)
        db.session.commit()

    login = client.post('/api/auth/login',
                        json={'username': 'viewer_role_test', 'password': 'viewpass'})
    assert login.status_code == 200
    viewer_token = login.get_json()['token']
    viewer_headers = {'Authorization': f'Bearer {viewer_token}',
                      'Content-Type': 'application/json'}

    resp = client.post('/api/pipelines', json={'name': 'Viewer Pipeline'}, headers=viewer_headers)
    assert resp.status_code == 403
    assert 'denied' in resp.get_json()['error'].lower()

    # Cleanup
    with app.app_context():
        from flowforge.db.models import User, db
        u = db.session.query(User).filter_by(username='viewer_role_test').first()
        if u:
            db.session.delete(u)
            db.session.commit()


def test_require_role_allows_editor(app, client):
    """An editor-role token must be allowed on editor-only endpoints."""
    import bcrypt

    with app.app_context():
        from flowforge.db.models import User, db
        editor = User(
            username='editor_role_test',
            password_hash=bcrypt.hashpw(b'editpass', bcrypt.gensalt(4)).decode(),
            role='editor',
        )
        db.session.add(editor)
        db.session.commit()

    login = client.post('/api/auth/login',
                        json={'username': 'editor_role_test', 'password': 'editpass'})
    assert login.status_code == 200
    editor_headers = {'Authorization': f'Bearer {login.get_json()["token"]}',
                      'Content-Type': 'application/json'}

    resp = client.post('/api/pipelines',
                       json={'name': 'Editor Pipeline'},
                       headers=editor_headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    client.delete(f'/api/pipelines/{pid}', headers=editor_headers)

    with app.app_context():
        from flowforge.db.models import User, db
        u = db.session.query(User).filter_by(username='editor_role_test').first()
        if u:
            db.session.delete(u)
            db.session.commit()
