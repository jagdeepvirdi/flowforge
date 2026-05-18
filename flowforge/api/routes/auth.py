"""Auth routes — POST /api/auth/login."""
from flask import Blueprint, jsonify, request

from flowforge.api.auth import login as auth_login

bp = Blueprint('auth', __name__)


@bp.post('/auth/login')
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    token = auth_login(username, password)
    if not token:
        return jsonify({'error': 'Invalid username or password'}), 401

    return jsonify({'token': token})
