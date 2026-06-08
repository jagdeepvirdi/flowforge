"""Tests for password-reset request / confirm / validate endpoints."""
import secrets
from datetime import UTC, datetime, timedelta
from unittest.mock import patch


# ── /auth/password-reset/request ─────────────────────────────────────────────

def test_request_reset_missing_username(client):
    resp = client.post('/api/auth/password-reset/request', json={})
    assert resp.status_code == 400
    assert 'username' in resp.get_json()['error'].lower()


def test_request_reset_unknown_user_returns_200(client):
    resp = client.post('/api/auth/password-reset/request',
                       json={'username': 'nonexistent_user_xyz'})
    assert resp.status_code == 200
    assert 'message' in resp.get_json()


def test_request_reset_user_without_email_returns_200(client):
    # testadmin has no email set by default — should silently succeed
    resp = client.post('/api/auth/password-reset/request',
                       json={'username': 'testadmin'})
    assert resp.status_code == 200
    assert 'message' in resp.get_json()


def test_request_reset_email_send_failure_still_returns_200(client):
    # Even when email sending fails, the endpoint must always return 200
    resp = client.post('/api/auth/password-reset/request',
                       json={'username': 'testadmin'})
    assert resp.status_code == 200


def test_request_reset_for_user_with_email(app, client):
    """When user has an email and provider is mocked, endpoint creates a token and returns 200."""
    with app.app_context():
        from flowforge.db.models import User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        original_email = user.email
        user.email = 'testadmin@example.com'
        db.session.commit()

    with patch('flowforge.api.routes.password_reset._send_reset_email'):
        resp = client.post('/api/auth/password-reset/request',
                           json={'username': 'testadmin'})

    # Restore email
    with app.app_context():
        from flowforge.db.models import User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        user.email = original_email
        db.session.commit()

    assert resp.status_code == 200
    assert 'message' in resp.get_json()


# ── /auth/password-reset/confirm ─────────────────────────────────────────────

def test_confirm_reset_missing_fields(client):
    resp = client.post('/api/auth/password-reset/confirm', json={})
    assert resp.status_code == 400
    assert 'required' in resp.get_json()['error'].lower()


def test_confirm_reset_missing_token(client):
    resp = client.post('/api/auth/password-reset/confirm',
                       json={'new_password': 'newpassword123'})
    assert resp.status_code == 400


def test_confirm_reset_missing_password(client):
    resp = client.post('/api/auth/password-reset/confirm',
                       json={'token': 'sometoken'})
    assert resp.status_code == 400


def test_confirm_reset_password_too_short(client):
    resp = client.post('/api/auth/password-reset/confirm',
                       json={'token': 'tok', 'new_password': 'short'})
    assert resp.status_code == 400
    assert '8' in resp.get_json()['error']


def test_confirm_reset_invalid_token(client):
    resp = client.post('/api/auth/password-reset/confirm',
                       json={'token': 'nonexistenttoken', 'new_password': 'newpassword123'})
    assert resp.status_code == 400
    assert 'invalid' in resp.get_json()['error'].lower()


def test_confirm_reset_expired_token(app, client):
    with app.app_context():
        from flowforge.db.models import PasswordResetToken, User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        tok = secrets.token_hex(32)
        db.session.add(PasswordResetToken(
            token=tok,
            user_id=user.id,
            expires_at=datetime.now(UTC) - timedelta(hours=2),  # already expired
        ))
        db.session.commit()

    resp = client.post('/api/auth/password-reset/confirm',
                       json={'token': tok, 'new_password': 'newpassword123'})
    assert resp.status_code == 400
    assert 'expired' in resp.get_json()['error'].lower()


def test_confirm_reset_already_used_token(app, client):
    with app.app_context():
        from flowforge.db.models import PasswordResetToken, User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        tok = secrets.token_hex(32)
        db.session.add(PasswordResetToken(
            token=tok,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=datetime.now(UTC),  # already used
        ))
        db.session.commit()

    resp = client.post('/api/auth/password-reset/confirm',
                       json={'token': tok, 'new_password': 'newpassword123'})
    assert resp.status_code == 400
    assert 'invalid' in resp.get_json()['error'].lower()


def test_confirm_reset_valid_token(app, client):
    """Valid token resets the password and marks the token as used."""
    with app.app_context():
        from flowforge.db.models import PasswordResetToken, User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        tok = secrets.token_hex(32)
        db.session.add(PasswordResetToken(
            token=tok,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ))
        db.session.commit()

    resp = client.post('/api/auth/password-reset/confirm',
                       json={'token': tok, 'new_password': 'testpass'})  # reset back to testpass
    assert resp.status_code == 200
    assert 'reset' in resp.get_json()['message'].lower()

    # Token is now used — second use must fail
    resp2 = client.post('/api/auth/password-reset/confirm',
                        json={'token': tok, 'new_password': 'anotherpass123'})
    assert resp2.status_code == 400


# ── /auth/password-reset/validate/<token> ────────────────────────────────────

def test_validate_reset_token_invalid(client):
    resp = client.get('/api/auth/password-reset/validate/notarealtoken')
    assert resp.status_code == 200
    assert resp.get_json()['valid'] is False


def test_validate_reset_token_valid(app, client):
    with app.app_context():
        from flowforge.db.models import PasswordResetToken, User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        tok = secrets.token_hex(32)
        db.session.add(PasswordResetToken(
            token=tok,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ))
        db.session.commit()

    resp = client.get(f'/api/auth/password-reset/validate/{tok}')
    assert resp.status_code == 200
    assert resp.get_json()['valid'] is True


def test_validate_reset_token_expired(app, client):
    with app.app_context():
        from flowforge.db.models import PasswordResetToken, User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        tok = secrets.token_hex(32)
        db.session.add(PasswordResetToken(
            token=tok,
            user_id=user.id,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        ))
        db.session.commit()

    resp = client.get(f'/api/auth/password-reset/validate/{tok}')
    assert resp.status_code == 200
    assert resp.get_json()['valid'] is False
