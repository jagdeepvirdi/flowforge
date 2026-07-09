"""Auth login endpoint and OAuth2 setup stubs."""
import os

from flask import Blueprint, jsonify, request

from flowforge.api.auth import login, require_auth
from flowforge.engine.settings import get_audit_retention_days, get_run_retention_days

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
    from flowforge.db.models import User, db
    header = req.headers.get('Authorization', '')
    token = header[len('Bearer '):]
    payload = verify_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token'}), 401
    user = db.session.query(User).filter_by(username=payload.get('sub')).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'token': generate_token(user)})


def _ai_enabled() -> bool:
    val = os.environ.get('FLOWFORGE_AI_ENABLED', 'true').lower().strip()
    return val not in ('false', '0', 'no', 'off')


@bp.get('/setup/status')
@require_auth
def setup_status():
    """Return which OAuth providers are fully configured via env vars, and other system info."""
    def _all(*keys: str) -> bool:
        return all(os.environ.get(k, '').strip() for k in keys)

    return jsonify({
        'gmail': {
            'configured': _all('GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 'GMAIL_REFRESH_TOKEN', 'GMAIL_SENDER'),
            'sender': os.environ.get('GMAIL_SENDER', ''),
        },
        'drive': {
            'configured': _all('GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 'GMAIL_REFRESH_TOKEN'),
            'folder_id': os.environ.get('GOOGLE_DRIVE_FOLDER_ID', ''),
        },
        'microsoft365': {
            'configured': _all('MICROSOFT_TENANT_ID', 'MICROSOFT_CLIENT_ID', 'MICROSOFT_CLIENT_SECRET', 'MICROSOFT_SENDER_EMAIL'),
            'sender': os.environ.get('MICROSOFT_SENDER_EMAIL', ''),
        },
        'ai': {
            'enabled': _ai_enabled(),
            'ollama_url': os.environ.get('OLLAMA_URL', 'http://localhost:11434'),
            'model': os.environ.get('OLLAMA_QUERY_MODEL', 'llama3.2:3b'),
            'claude': {
                'configured': _all('ANTHROPIC_API_KEY'),
            },
            'gemini': {
                'configured': _all('GEMINI_API_KEY'),
                'model': os.environ.get('GEMINI_QUERY_MODEL', 'gemini-2.5-flash'),
            },
        },
        'retention': {
            'run_days': get_run_retention_days(),
            'audit_days': get_audit_retention_days(),
        },
        'encrypt_output': os.environ.get('FLOWFORGE_ENCRYPT_OUTPUT', '').lower() == 'true',
    })


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
