"""Auth login endpoint and OAuth2 setup stubs."""
from flask import Blueprint, jsonify, request

from flowforge.api.auth import login, require_auth

bp = Blueprint('setup', __name__)


@bp.post('/auth/login')
def auth_login():
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'username and password are required'}), 400

    token = login(username, password)
    if not token:
        return jsonify({'error': 'Invalid credentials'}), 401

    return jsonify({'token': token})


@bp.post('/auth/refresh')
@require_auth
def auth_refresh():
    from flask import request as req
    from flowforge.api.auth import generate_token, verify_token
    header = req.headers.get('Authorization', '')
    token = header[len('Bearer '):]
    username = verify_token(token)
    if not username:
        return jsonify({'error': 'Invalid token'}), 401
    return jsonify({'token': generate_token(username)})


@bp.post('/setup/gmail')
@require_auth
def setup_gmail():
    """OAuth2 setup for Gmail — full flow implemented in CLI (flowforge setup gmail)."""
    return jsonify({'message': 'Run `flowforge setup gmail` in your terminal to complete Gmail OAuth2 setup.'}), 200


@bp.post('/setup/microsoft365')
@require_auth
def setup_microsoft365():
    """OAuth2 setup for Microsoft 365 — full flow implemented in CLI."""
    return jsonify({'message': 'Run `flowforge setup microsoft365` in your terminal to complete Microsoft 365 OAuth2 setup.'}), 200
