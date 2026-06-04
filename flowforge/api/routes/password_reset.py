"""Password reset — request token via email, confirm with new password.

Flow:
  1. POST /api/auth/password-reset/request  { username }
       → if user has email, sends a reset link; always returns 200 (don't leak existence)
  2. POST /api/auth/password-reset/confirm  { token, new_password }
       → validates token (1h TTL, single-use), sets new password

Email is sent via the configured default email provider.
Token is delivered in the link: {FLOWFORGE_APP_URL}/#reset_token=<token>
"""
import os
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from flask import Blueprint, jsonify, request

import flowforge.audit as audit
from flowforge.db.models import PasswordResetToken, User, db

bp = Blueprint('password_reset', __name__)

_TOKEN_TTL_HOURS = 1
_MIN_PW_LEN      = 8


def _app_url() -> str:
    return os.environ.get('FLOWFORGE_APP_URL', 'http://localhost:5000').rstrip('/')


def _send_reset_email(user: User, token: str) -> None:
    """Send the password reset email using the default email provider."""
    reset_link = f"{_app_url()}/#reset_token={token}"
    subject    = "FlowForge — Password Reset"
    html_body  = f"""
    <div style="font-family: Inter, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; color: #F1F5F9; background: #1A1D27; border-radius: 8px;">
      <div style="margin-bottom: 24px;">
        <span style="font-size: 20px; font-weight: 600; color: #F97316;">FlowForge</span>
      </div>
      <h2 style="font-size: 16px; font-weight: 600; margin: 0 0 12px; color: #F1F5F9;">Password Reset Request</h2>
      <p style="font-size: 13px; color: #94A3B8; margin: 0 0 20px; line-height: 1.6;">
        A password reset was requested for the account <strong>{user.username}</strong>.
        Click the button below to set a new password. This link expires in {_TOKEN_TTL_HOURS} hour.
      </p>
      <a href="{reset_link}" style="display: inline-block; background: #F97316; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-size: 13px; font-weight: 600;">
        Reset Password
      </a>
      <p style="font-size: 12px; color: #64748B; margin: 20px 0 0; line-height: 1.6;">
        If you did not request a password reset, ignore this email — your password will not change.
      </p>
    </div>
    """

    try:
        from flowforge.db.models import EmailProvider
        from flowforge.email_providers.factory import get_provider
        provider_row = db.session.query(EmailProvider).filter_by(is_default=True).first()
        if not provider_row:
            provider_row = db.session.query(EmailProvider).first()
        if not provider_row:
            raise RuntimeError("No email provider configured")

        provider = get_provider(provider_row)
        result   = provider.send(
            to=[user.email],
            cc=[], bcc=[],
            subject=subject,
            html_body=html_body,
            attachments=[],
        )
        if not result.success:
            raise RuntimeError(result.error or "Send failed")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            "Password reset email failed for user %s", user.username
        )
        raise exc


@bp.post('/auth/password-reset/request')
def request_reset():
    data     = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()

    if not username:
        return jsonify({'error': 'username is required'}), 400

    # Always respond 200 — don't reveal whether account/email exists
    user = db.session.query(User).filter_by(username=username).first()
    if not user or not user.email:
        return jsonify({'message': 'If an account with that username and a registered email exists, a reset link has been sent.'})

    # Expire any existing unused tokens for this user
    (db.session.query(PasswordResetToken)
     .filter_by(user_id=user.id)
     .filter(PasswordResetToken.used_at.is_(None))
     .update({'expires_at': datetime.now(UTC)}, synchronize_session=False))

    token      = secrets.token_hex(32)
    expires_at = datetime.now(UTC) + timedelta(hours=_TOKEN_TTL_HOURS)
    db.session.add(PasswordResetToken(token=token, user_id=user.id, expires_at=expires_at))
    db.session.commit()

    try:
        _send_reset_email(user, token)
    except Exception:
        return jsonify({'message': 'If an account with that username and a registered email exists, a reset link has been sent.'})

    audit.log_pipeline_change('PASSWORD_RESET_REQUESTED', user.username, user.id)
    return jsonify({'message': 'If an account with that username and a registered email exists, a reset link has been sent.'})


@bp.post('/auth/password-reset/confirm')
def confirm_reset():
    data         = request.get_json(silent=True) or {}
    token_val    = (data.get('token') or '').strip()
    new_password = data.get('new_password') or ''

    if not token_val or not new_password:
        return jsonify({'error': 'token and new_password are required'}), 400
    if len(new_password) < _MIN_PW_LEN:
        return jsonify({'error': f'new_password must be at least {_MIN_PW_LEN} characters'}), 400

    now   = datetime.now(UTC)
    entry = db.session.get(PasswordResetToken, token_val)

    if not entry or entry.used_at is not None or entry.expires_at < now:
        return jsonify({'error': 'Invalid or expired reset token'}), 400

    user = db.session.get(User, entry.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    entry.used_at      = now
    db.session.commit()

    audit.log_pipeline_change('PASSWORD_RESET_COMPLETED', user.username, user.id)
    return jsonify({'message': 'Password reset successfully. You can now log in.'})


@bp.get('/auth/password-reset/validate/<token>')
def validate_reset_token(token: str):
    """Check whether a reset token is still valid (used by the frontend before showing the form)."""
    now   = datetime.now(UTC)
    entry = db.session.get(PasswordResetToken, token)
    valid = bool(entry and entry.used_at is None and entry.expires_at >= now)
    return jsonify({'valid': valid})
