"""Auth routes — POST /api/auth/login, POST /api/auth/logout."""
from flask import Blueprint, g, jsonify, request

from flowforge.api.app import limiter
from flowforge.api.auth import login as auth_login
from flowforge.api.auth import require_auth, revoke_token
from flowforge import audit

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
