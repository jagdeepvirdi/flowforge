"""MFA (TOTP) endpoints — enroll, confirm, disable, verify, use-backup."""
import json
import os
import secrets

import bcrypt
from flask import Blueprint, g, jsonify, request

import flowforge.audit as audit
from flowforge.api.auth import (
    generate_token,
    require_auth,
    verify_mfa_token,
)
from flowforge.crypto import decrypt_value, encrypt_value
from flowforge.db.models import User, db

bp = Blueprint('mfa', __name__)

_MFA_BACKUP_COUNT = 10
_BACKUP_CODE_LEN  = 8   # hex chars per segment


def _generate_backup_codes() -> list[str]:
    """Return a list of one-time backup codes in the form XXXX-XXXX."""
    return [
        f'{secrets.token_hex(4)[:4].upper()}-{secrets.token_hex(4)[:4].upper()}'
        for _ in range(_MFA_BACKUP_COUNT)
    ]


def _load_backup_codes(user: User) -> list[str]:
    if not user.mfa_backup_codes:
        return []
    try:
        return json.loads(decrypt_value(user.mfa_backup_codes))
    except Exception:
        return []


def _save_backup_codes(user: User, codes: list[str]) -> None:
    user.mfa_backup_codes = encrypt_value(json.dumps(codes))


@bp.get('/auth/mfa/status')
@require_auth
def mfa_status():
    """Return the MFA state for the current user."""
    user = db.session.get(User, g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'mfa_enabled': user.mfa_enabled,
        'sso_provider': user.sso_provider,
    })


@bp.post('/auth/mfa/enroll')
@require_auth
def mfa_enroll():
    """Generate a TOTP secret and return the provisioning URI.

    Call this to begin enrollment.  The secret is stored un-activated until
    the user confirms a correct code via POST /auth/mfa/confirm.
    """
    try:
        import pyotp
    except ImportError:
        return jsonify({'error': 'pyotp not installed — run: pip install pyotp'}), 501

    user = db.session.get(User, g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    secret = pyotp.random_base32()
    user.mfa_secret = encrypt_value(secret)
    db.session.commit()

    issuer   = os.environ.get('FLOWFORGE_MFA_ISSUER', 'FlowForge')
    totp     = pyotp.TOTP(secret)
    uri      = totp.provisioning_uri(name=user.username, issuer_name=issuer)

    return jsonify({'provisioning_uri': uri, 'secret': secret})


@bp.post('/auth/mfa/confirm')
@require_auth
def mfa_confirm():
    """Verify a TOTP code and activate MFA, returning one-time backup codes."""
    try:
        import pyotp
    except ImportError:
        return jsonify({'error': 'pyotp not installed — run: pip install pyotp'}), 501

    user = db.session.get(User, g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if not user.mfa_secret:
        return jsonify({'error': 'MFA enrollment not started — call POST /auth/mfa/enroll first'}), 400

    data = request.get_json(silent=True) or {}
    code = str(data.get('code', '')).strip().replace(' ', '')
    if not code:
        return jsonify({'error': 'code is required'}), 400

    secret = decrypt_value(user.mfa_secret)
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        return jsonify({'error': 'Invalid code — check your authenticator app and try again'}), 400

    backup_codes = _generate_backup_codes()
    user.mfa_enabled = True
    _save_backup_codes(user, backup_codes)
    db.session.commit()

    audit.log_pipeline_change('MFA_ENABLED', user.username, user.id)

    return jsonify({'backup_codes': backup_codes})


@bp.post('/auth/mfa/disable')
@require_auth
def mfa_disable():
    """Disable MFA for the current user (requires current password for confirmation)."""
    user = db.session.get(User, g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    if not password:
        return jsonify({'error': 'password is required to disable MFA'}), 400

    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({'error': 'Incorrect password'}), 401

    user.mfa_enabled      = False
    user.mfa_secret       = None
    user.mfa_backup_codes = None
    db.session.commit()

    audit.log_pipeline_change('MFA_DISABLED', user.username, user.id)

    return jsonify({'message': 'MFA disabled'})


@bp.post('/auth/mfa/verify')
def mfa_verify():
    """Second step of MFA login — exchange a MFA challenge token + TOTP code for a full JWT."""
    try:
        import pyotp
    except ImportError:
        return jsonify({'error': 'pyotp not installed — run: pip install pyotp'}), 501

    data = request.get_json(silent=True) or {}
    mfa_token = data.get('mfa_token', '')
    code      = str(data.get('code', '')).strip().replace(' ', '')

    if not mfa_token or not code:
        return jsonify({'error': 'mfa_token and code are required'}), 400

    payload = verify_mfa_token(mfa_token)
    if not payload:
        return jsonify({'error': 'Invalid or expired MFA challenge token'}), 401

    user = db.session.query(User).filter_by(username=payload['sub']).first()
    if not user or not user.mfa_enabled or not user.mfa_secret:
        return jsonify({'error': 'MFA not configured for this account'}), 400

    secret = decrypt_value(user.mfa_secret)
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        return jsonify({'error': 'Invalid TOTP code'}), 401

    return jsonify({'token': generate_token(user)})


@bp.post('/auth/mfa/use-backup')
def mfa_use_backup():
    """Second step of MFA login using a one-time backup code."""
    data = request.get_json(silent=True) or {}
    mfa_token   = data.get('mfa_token', '')
    backup_code = str(data.get('backup_code', '')).strip().upper()

    if not mfa_token or not backup_code:
        return jsonify({'error': 'mfa_token and backup_code are required'}), 400

    payload = verify_mfa_token(mfa_token)
    if not payload:
        return jsonify({'error': 'Invalid or expired MFA challenge token'}), 401

    user = db.session.query(User).filter_by(username=payload['sub']).first()
    if not user or not user.mfa_enabled:
        return jsonify({'error': 'MFA not configured for this account'}), 400

    codes = _load_backup_codes(user)
    if backup_code not in codes:
        return jsonify({'error': 'Invalid or already-used backup code'}), 401

    codes.remove(backup_code)
    _save_backup_codes(user, codes)
    db.session.commit()

    audit.log_pipeline_change('MFA_BACKUP_CODE_USED', user.username, user.id)

    return jsonify({'token': generate_token(user), 'backup_codes_remaining': len(codes)})
