"""Auth routes — POST /api/auth/login."""
from flask import Blueprint, jsonify, request

from flowforge.api.app import limiter
from flowforge.api.auth import login as auth_login
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

    token = auth_login(username, password)
    audit.log_login(username, success=token is not None, remote_addr=remote_addr)

    if not token:
        return jsonify({'error': 'Invalid username or password'}), 401

    return jsonify({'token': token})
