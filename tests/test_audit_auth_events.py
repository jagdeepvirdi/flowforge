"""Account-security events must be audited under their own action names.

MFA, password-reset and first-time SSO events used to go through log_pipeline_change(), so they
were filed as PIPELINE_CFG_MFA_ENABLED etc. (the same miscategorisation the 2026-07 audit fixed for
user events). docs/security.md and docs/data-flow.md document the bare names asserted here.
"""
import ast
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flowforge import audit
from flowforge.db.models import AuditLog, PasswordResetToken, User, db
from flowforge.user_admin import create_user, delete_user

ROOT = Path(__file__).resolve().parent.parent


def _name(prefix='aa'):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'


def _since():
    return datetime.now(UTC) - timedelta(seconds=5)


def _events(app, name, since):
    """(action, actor) of every audit row about `name` written since `since`."""
    with app.app_context():
        rows = (db.session.query(AuditLog)
                .filter(AuditLog.details['name'].astext == name, AuditLog.timestamp >= since)
                .all())
        return [(r.action, r.username) for r in rows]


def _assert_filed_as(app, name, since, action, actor=None):
    events = _events(app, name, since)
    assert action in [a for a, _ in events], f'{action} missing from {events}'
    assert not [a for a, _ in events if a.startswith('PIPELINE_CFG_')], f'miscategorised: {events}'
    if actor is not None:
        assert (action, actor) in events


@pytest.fixture
def fresh_user(app):
    """A throwaway user with an email address, removed afterwards."""
    name = _name()
    with app.app_context():
        user, password = create_user(name, role='editor', email=f'{name}@example.com', must_change_password=False)
        uid = user.id
    yield {'name': name, 'id': uid, 'password': password}
    with app.app_context():
        delete_user(name)


# ── MFA ───────────────────────────────────────────────────────────────────────


def test_mfa_enable_and_disable_are_filed_as_mfa_events(app, client, headers):
    mock_pyotp = MagicMock()
    mock_pyotp.random_base32.return_value = 'TESTSECRETBASE32'
    totp = MagicMock()
    totp.provisioning_uri.return_value = 'otpauth://x'
    totp.verify.return_value = True
    mock_pyotp.TOTP.return_value = totp
    since = _since()
    try:
        with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
            assert client.post('/api/auth/mfa/enroll', headers=headers).status_code == 200
            assert client.post('/api/auth/mfa/confirm', json={'code': '123456'}, headers=headers).status_code == 200
        _assert_filed_as(app, 'testadmin', since, 'MFA_ENABLED', actor='testadmin')
    finally:
        assert client.post('/api/auth/mfa/disable', json={'password': 'testpass'}, headers=headers).status_code == 200
    _assert_filed_as(app, 'testadmin', since, 'MFA_DISABLED', actor='testadmin')


def test_mfa_backup_code_login_is_filed_as_mfa_event(app, client, fresh_user):
    from flowforge.api.auth import generate_mfa_token
    from flowforge.api.routes.mfa import _save_backup_codes
    since = _since()
    with app.app_context():
        user = db.session.query(User).filter_by(username=fresh_user['name']).first()
        user.mfa_enabled = True
        _save_backup_codes(user, ['ABCD1234'])
        db.session.commit()
        challenge = generate_mfa_token(user)
    resp = client.post('/api/auth/mfa/use-backup', json={'mfa_token': challenge, 'backup_code': 'abcd1234'})
    assert resp.status_code == 200
    # Nobody is signed in yet at this step, so the affected account is the recorded actor.
    _assert_filed_as(app, fresh_user['name'], since, 'MFA_BACKUP_CODE_USED', actor=fresh_user['name'])


# ── password reset ────────────────────────────────────────────────────────────


def test_password_reset_request_is_filed_as_its_own_event(app, client, fresh_user):
    since = _since()
    with patch('flowforge.api.routes.password_reset._send_reset_email'):
        resp = client.post('/api/auth/password-reset/request', json={'username': fresh_user['name']})
    assert resp.status_code == 200
    _assert_filed_as(app, fresh_user['name'], since, 'PASSWORD_RESET_REQUESTED', actor=fresh_user['name'])


def test_password_reset_completion_is_filed_as_its_own_event(app, client, fresh_user):
    since = _since()
    token = secrets.token_hex(32)
    with app.app_context():
        db.session.add(PasswordResetToken(token=token, user_id=fresh_user['id'],
                                          expires_at=datetime.now(UTC) + timedelta(hours=1)))
        db.session.commit()
    resp = client.post('/api/auth/password-reset/confirm', json={'token': token, 'new_password': 'brand-new-pass-1'})
    assert resp.status_code == 200
    _assert_filed_as(app, fresh_user['name'], since, 'PASSWORD_RESET_COMPLETED', actor=fresh_user['name'])


# ── SSO ───────────────────────────────────────────────────────────────────────


def test_first_sso_login_is_filed_as_sso_user_created(app, monkeypatch):
    from flowforge.api.routes.sso import _find_or_create_user
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    since = _since()
    email = f'sso_{uuid.uuid4().hex[:8]}@example.com'
    with app.app_context():
        user = _find_or_create_user(email, 'google')
        username = user.username
    try:
        _assert_filed_as(app, username, since, 'SSO_USER_CREATED', actor=username)
    finally:
        with app.app_context():
            delete_user(username)


# ── the helper itself ─────────────────────────────────────────────────────────


def test_log_auth_event_uses_the_bare_action_name():
    with patch.object(audit, '_write_db_audit') as write, patch.object(audit, '_get_logger'):
        audit.log_auth_event('mfa_enabled', 'alice', 'uid-1')
    assert write.call_args.args[0] == 'MFA_ENABLED'
    assert write.call_args.args[4] == {'name': 'alice', 'id': 'uid-1'}


def test_log_auth_event_keeps_the_authenticated_actor(app):
    with app.test_request_context():
        from flask import g
        g.user_token = {'sub': 'admin_actor'}
        g.current_user_id = 'actor-id'
        with patch.object(audit, '_write_db_audit') as write, patch.object(audit, '_get_logger'):
            audit.log_auth_event('MFA_DISABLED', 'subject', 'subject-id')
    assert write.call_args.args[1:3] == ('admin_actor', 'actor-id')


def test_log_auth_event_falls_back_to_the_subject_without_a_session():
    with patch.object(audit, '_write_db_audit') as write, patch.object(audit, '_get_logger'):
        audit.log_auth_event('PASSWORD_RESET_REQUESTED', 'bob', 'bob-id')
    assert write.call_args.args[1:3] == ('bob', 'bob-id')


# ── guard: only real pipeline changes may use log_pipeline_change ─────────────

PIPELINE_ACTIONS = {'CREATED', 'UPDATED', 'DELETED', 'CLONED', 'IMPORTED', 'PROMOTED'}


def test_log_pipeline_change_is_only_used_for_pipeline_changes():
    offenders = []
    for path in (ROOT / 'flowforge').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if (isinstance(node, ast.Call) and getattr(node.func, 'attr', None) == 'log_pipeline_change'
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value not in PIPELINE_ACTIONS):
                offenders.append(f'{path.relative_to(ROOT)}:{node.lineno} uses {node.args[0].value!r}')
    assert not offenders, ('Non-pipeline events filed as PIPELINE_CFG_*; use log_auth_event / log_user_change:\n'
                           + '\n'.join(offenders))
