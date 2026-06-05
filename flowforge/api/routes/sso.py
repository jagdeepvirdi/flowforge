"""SSO (OAuth2) login — Google and Microsoft.

Flows:
  Browser → GET /api/auth/sso/google → (redirect) → Google consent → GET /api/auth/sso/google/callback
                                                                     → redirect to frontend /#sso_token=<jwt>

Configure via environment variables:
  GOOGLE_SSO_CLIENT_ID / GOOGLE_SSO_CLIENT_SECRET
  MICROSOFT_SSO_TENANT_ID / MICROSOFT_SSO_CLIENT_ID / MICROSOFT_SSO_CLIENT_SECRET
  FLOWFORGE_APP_URL       — base URL of the frontend (default: http://localhost:5000)
  FLOWFORGE_SSO_AUTO_CREATE=true  — create user on first SSO login (default: false)
"""
import os
import secrets
import time

import bcrypt
from flask import Blueprint, jsonify, redirect, request

import flowforge.audit as audit
from flowforge.api.auth import generate_token
from flowforge.db.models import User, db

bp = Blueprint('sso', __name__)

# In-memory state store — prevents CSRF in the OAuth2 redirect flow.
# { state_token: (provider, expires_ts) }
_SSO_STATES: dict[str, tuple[str, float]] = {}
_STATE_TTL = 300  # 5 minutes


def _app_url() -> str:
    return os.environ.get('FLOWFORGE_APP_URL', 'http://localhost:5000').rstrip('/')


def _auto_create() -> bool:
    return os.environ.get('FLOWFORGE_SSO_AUTO_CREATE', '').lower() == 'true'


def _new_state(provider: str) -> str:
    token = secrets.token_urlsafe(24)
    _expire_states()
    _SSO_STATES[token] = (provider, time.monotonic() + _STATE_TTL)
    return token


def _consume_state(token: str) -> str | None:
    _expire_states()
    entry = _SSO_STATES.pop(token, None)
    if not entry:
        return None
    provider, exp = entry
    return provider if time.monotonic() < exp else None


def _expire_states() -> None:
    now = time.monotonic()
    expired = [k for k, (_, exp) in _SSO_STATES.items() if now >= exp]
    for k in expired:
        del _SSO_STATES[k]


def _find_or_create_user(email: str, provider: str) -> User | None:
    """Return a User for the given SSO email, or create one if FLOWFORGE_SSO_AUTO_CREATE=true."""
    user = db.session.query(User).filter_by(sso_email=email).first()
    if user:
        return user

    # Check if a user with a matching username (email prefix) already exists
    username = email.split('@')[0]
    existing = db.session.query(User).filter_by(username=username).first()

    if not _auto_create():
        # Link to an exact username match if found, otherwise deny
        if existing and not existing.sso_email:
            existing.sso_provider = provider
            existing.sso_email    = email
            db.session.commit()
            return existing
        return None

    if existing:
        username = email  # use full email as username to avoid collision

    dummy_hash = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()
    user = User(
        username=username, password_hash=dummy_hash,
        role='viewer', sso_provider=provider, sso_email=email,
    )
    db.session.add(user)
    db.session.commit()
    audit.log_pipeline_change('SSO_USER_CREATED', username, user.id)
    return user


def _redirect_with_token(token: str):
    return redirect(f'{_app_url()}/#sso_token={token}')


def _redirect_with_error(msg: str):
    return redirect(f'{_app_url()}/#sso_error={msg}')


# ── Google SSO ────────────────────────────────────────────────────────────────

def _google_configured() -> bool:
    return bool(
        os.environ.get('GOOGLE_SSO_CLIENT_ID')
        and os.environ.get('GOOGLE_SSO_CLIENT_SECRET')
    )


@bp.get('/auth/sso/google')
def sso_google_start():
    if not _google_configured():
        return jsonify({'error': 'Google SSO is not configured'}), 501
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        return jsonify({'error': 'google-auth-oauthlib not installed'}), 501

    state = _new_state('google')
    callback = f'{_app_url()}/api/auth/sso/google/callback'

    flow = Flow.from_client_config(
        {
            'web': {
                'client_id':     os.environ['GOOGLE_SSO_CLIENT_ID'],
                'client_secret': os.environ['GOOGLE_SSO_CLIENT_SECRET'],
                'auth_uri':      'https://accounts.google.com/o/oauth2/auth',
                'token_uri':     'https://oauth2.googleapis.com/token',
                'redirect_uris': [callback],
            }
        },
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'],
    )
    flow.redirect_uri = callback
    auth_url, _ = flow.authorization_url(state=state, access_type='online', prompt='select_account')
    return redirect(auth_url)


@bp.get('/auth/sso/google/callback')
def sso_google_callback():
    if not _google_configured():
        return _redirect_with_error('Google+SSO+not+configured')

    state = request.args.get('state', '')
    provider = _consume_state(state)
    if provider != 'google':
        return _redirect_with_error('Invalid+or+expired+SSO+state')

    error = request.args.get('error')
    if error:
        return _redirect_with_error(error)

    try:
        from google_auth_oauthlib.flow import Flow

        callback = f'{_app_url()}/api/auth/sso/google/callback'
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id':     os.environ['GOOGLE_SSO_CLIENT_ID'],
                    'client_secret': os.environ['GOOGLE_SSO_CLIENT_SECRET'],
                    'auth_uri':      'https://accounts.google.com/o/oauth2/auth',
                    'token_uri':     'https://oauth2.googleapis.com/token',
                    'redirect_uris': [callback],
                }
            },
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile'],
            state=state,
        )
        flow.redirect_uri = callback
        flow.fetch_token(authorization_response=request.url)

        import requests as req_lib
        resp = req_lib.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {flow.credentials.token}'},
            timeout=10,
        )
        resp.raise_for_status()
        info = resp.json()
        email = info.get('email', '').lower().strip()
    except Exception as exc:
        return _redirect_with_error(f'Google+token+exchange+failed: {exc}')

    if not email:
        return _redirect_with_error('No+email+returned+from+Google')

    user = _find_or_create_user(email, 'google')
    if not user:
        return _redirect_with_error('Account+not+found.+Contact+your+administrator.')

    audit.log_login(user.username, success=True, remote_addr=request.remote_addr or '')
    return _redirect_with_token(generate_token(user))


# ── Microsoft SSO ─────────────────────────────────────────────────────────────

def _microsoft_configured() -> bool:
    return bool(
        os.environ.get('MICROSOFT_SSO_TENANT_ID')
        and os.environ.get('MICROSOFT_SSO_CLIENT_ID')
        and os.environ.get('MICROSOFT_SSO_CLIENT_SECRET')
    )


@bp.get('/auth/sso/microsoft')
def sso_microsoft_start():
    if not _microsoft_configured():
        return jsonify({'error': 'Microsoft SSO is not configured'}), 501
    try:
        import msal
    except ImportError:
        return jsonify({'error': 'msal not installed'}), 501

    state    = _new_state('microsoft')
    callback = f'{_app_url()}/api/auth/sso/microsoft/callback'
    scopes   = ['openid', 'email', 'profile', 'User.Read']

    cca = msal.ConfidentialClientApplication(
        client_id=os.environ['MICROSOFT_SSO_CLIENT_ID'],
        client_credential=os.environ['MICROSOFT_SSO_CLIENT_SECRET'],
        authority=f'https://login.microsoftonline.com/{os.environ["MICROSOFT_SSO_TENANT_ID"]}',
    )
    auth_url = cca.get_authorization_request_url(
        scopes=scopes, state=state, redirect_uri=callback,
    )
    return redirect(auth_url)


@bp.get('/auth/sso/microsoft/callback')
def sso_microsoft_callback():
    if not _microsoft_configured():
        return _redirect_with_error('Microsoft+SSO+not+configured')

    state = request.args.get('state', '')
    provider = _consume_state(state)
    if provider != 'microsoft':
        return _redirect_with_error('Invalid+or+expired+SSO+state')

    error = request.args.get('error')
    if error:
        return _redirect_with_error(request.args.get('error_description', error))

    code = request.args.get('code', '')
    if not code:
        return _redirect_with_error('No+authorization+code+returned')

    try:
        import msal
        callback = f'{_app_url()}/api/auth/sso/microsoft/callback'
        cca = msal.ConfidentialClientApplication(
            client_id=os.environ['MICROSOFT_SSO_CLIENT_ID'],
            client_credential=os.environ['MICROSOFT_SSO_CLIENT_SECRET'],
            authority=f'https://login.microsoftonline.com/{os.environ["MICROSOFT_SSO_TENANT_ID"]}',
        )
        result = cca.acquire_token_by_authorization_code(
            code=code,
            scopes=['openid', 'email', 'profile', 'User.Read'],
            redirect_uri=callback,
        )
    except Exception as exc:
        return _redirect_with_error(f'Microsoft+token+exchange+failed: {exc}')

    if 'error' in result:
        return _redirect_with_error(result.get('error_description', result['error']))

    claims = result.get('id_token_claims', {})
    email  = (claims.get('email') or claims.get('preferred_username', '')).lower().strip()

    if not email:
        return _redirect_with_error('No+email+in+Microsoft+token')

    user = _find_or_create_user(email, 'microsoft')
    if not user:
        return _redirect_with_error('Account+not+found.+Contact+your+administrator.')

    audit.log_login(user.username, success=True, remote_addr=request.remote_addr or '')
    return _redirect_with_token(generate_token(user))


# ── SSO config status (used by Login page to show/hide buttons) ───────────────

@bp.get('/auth/sso/providers')
def sso_providers():
    """Return which SSO providers are configured (no auth required — called from login page)."""
    return jsonify({
        'google':    _google_configured(),
        'microsoft': _microsoft_configured(),
    })
