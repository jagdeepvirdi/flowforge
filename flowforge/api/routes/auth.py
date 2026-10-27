"""Auth routes — POST /api/auth/login, POST /api/auth/logout."""
import bcrypt
from flask import Blueprint, g, jsonify, request

from flowforge import audit
from flowforge.api.app import limiter
from flowforge.api.auth import generate_token, require_auth, revoke_token, verify_pwchange_token
from flowforge.api.auth import login as auth_login
from flowforge.db.models import User, db

bp = Blueprint('auth', __name__)


@bp.post('/auth/login')
@limiter.limit('10 per minute')
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remote_addr = request.remote_addr or ''

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    result = auth_login(username, password)
    audit.log_login(username, success=result is not None, remote_addr=remote_addr)

    if not result:
        return jsonify({'error': 'Invalid username or password'}), 401

    # MFA second step required — return challenge token instead of full JWT
    if isinstance(result, dict):
        return jsonify(result)

    return jsonify({'token': result})


@bp.post('/auth/change-required-password')
@limiter.limit('10 per minute')
def change_required_password():
    """Second step of login when the account is flagged must_change_password
    (e.g. an admin-invited user who logged in with the password the admin set).
    Consumes the short-lived change_token from login() and issues a full session."""
    data = request.get_json(silent=True) or {}
    change_token = data.get('change_token') or ''
    new_password = data.get('new_password') or ''

    if not change_token or not new_password:
        return jsonify({'error': 'change_token and new_password are required'}), 400
    if len(new_password) < 8:
        return jsonify({'error': 'new_password must be at least 8 characters'}), 400

    payload = verify_pwchange_token(change_token)
    if not payload:
        return jsonify({'error': 'Invalid or expired token'}), 401

    user = db.session.get(User, payload.get('uid'))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    user.must_change_password = False
    db.session.commit()
    audit.log_user_change('PASSWORD_CHANGED', user.username, user.id)

    return jsonify({'token': generate_token(user)})


@bp.get('/auth/me')
@require_auth
def me():
    uid = g.user_token.get('uid')
    if not uid:
        return jsonify({'error': 'Token predates multi-user support — please log in again'}), 401
    return jsonify({
        'id': uid,
        'username': g.user_token.get('sub'),
        'role': g.user_token.get('role', 'viewer'),
    })


@bp.post('/auth/logout')
@require_auth
def logout():
    header = request.headers.get('Authorization', '')
    token = header[len('Bearer '):]
    username = revoke_token(token) or 'unknown'
    audit.log_logout(username, remote_addr=request.remote_addr or '')
    return jsonify({'message': 'Logged out'})
