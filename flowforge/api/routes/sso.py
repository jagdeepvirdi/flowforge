"""SSO login — Google, Microsoft (OAuth2) and SAML 2.0 (enterprise IdP).

Flows:
  Browser → GET /api/auth/sso/google → (redirect) → Google consent → GET /api/auth/sso/google/callback
                                                                     → redirect to frontend /#sso_token=<jwt>
  Browser → GET /api/auth/sso/saml/login → (redirect) → IdP login → POST /api/auth/sso/saml/acs
                                                                    → redirect to frontend /#sso_token=<jwt>

Configure via environment variables:
  GOOGLE_SSO_CLIENT_ID / GOOGLE_SSO_CLIENT_SECRET
  MICROSOFT_SSO_TENANT_ID / MICROSOFT_SSO_CLIENT_ID / MICROSOFT_SSO_CLIENT_SECRET
  SAML_SP_ENTITY_ID / SAML_IDP_ENTITY_ID / SAML_IDP_SSO_URL / SAML_IDP_X509_CERT
  FLOWFORGE_APP_URL       — base URL of the frontend (default: http://localhost:5000)
  FLOWFORGE_SSO_AUTO_CREATE=true  — create user on first SSO login (default: false)
"""
import os
import secrets
import time

import bcrypt
from flask import Blueprint, Response, jsonify, redirect, request

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
                'token_uri':     'https://oauth2.googleapis.com/token',  # nosec B105 — public endpoint URL, not a secret
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
                    'token_uri':     'https://oauth2.googleapis.com/token',  # nosec B105 — public endpoint URL, not a secret
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


# ── SAML SSO (enterprise IdP: Okta, Azure AD, PingFederate, ...) ──────────────

def _saml_configured() -> bool:
    return bool(
        os.environ.get('SAML_SP_ENTITY_ID')
        and os.environ.get('SAML_IDP_ENTITY_ID')
        and os.environ.get('SAML_IDP_SSO_URL')
        and os.environ.get('SAML_IDP_X509_CERT')
    )


def _saml_acs_url() -> str:
    return f'{_app_url()}/api/auth/sso/saml/acs'


def _saml_settings() -> dict:
    return {
        'strict': True,
        'debug': False,
        'sp': {
            'entityId': os.environ['SAML_SP_ENTITY_ID'],
            'assertionConsumerService': {
                'url':     _saml_acs_url(),
                'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
            },
            'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
        },
        'idp': {
            'entityId': os.environ['SAML_IDP_ENTITY_ID'],
            'singleSignOnService': {
                'url':     os.environ['SAML_IDP_SSO_URL'],
                'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
            },
            'x509cert': os.environ['SAML_IDP_X509_CERT'],
        },
        # SP does not sign requests (no SP key configured) — IdP assertions must be signed.
        'security': {
            'wantAssertionsSigned':  True,
            'wantNameIdEncrypted':   False,
            'authnRequestsSigned':   False,
            'logoutRequestSigned':   False,
            'logoutResponseSigned':  False,
        },
    }


def _saml_prepare_flask_request(req) -> dict:
    """Build the plain-dict request shape python3-saml expects (framework-agnostic)."""
    host, _, port = req.host.partition(':')
    return {
        'https':       'on' if req.scheme == 'https' else 'off',
        'http_host':   host,
        'server_port': port or ('443' if req.scheme == 'https' else '80'),
        'script_name': req.path,
        'get_data':    req.args.copy(),
        'post_data':   req.form.copy(),
    }


@bp.get('/auth/sso/saml/login')
def sso_saml_start():
    if not _saml_configured():
        return jsonify({'error': 'SAML SSO is not configured'}), 501
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except ImportError:
        return jsonify({'error': 'python3-saml not installed'}), 501

    state = _new_state('saml')
    saml_auth = OneLogin_Saml2_Auth(_saml_prepare_flask_request(request), _saml_settings())
    return redirect(saml_auth.login(return_to=state))


@bp.post('/auth/sso/saml/acs')
def sso_saml_acs():
    """Assertion Consumer Service — the IdP POSTs the SAMLResponse here."""
    if not _saml_configured():
        return _redirect_with_error('SAML+SSO+not+configured')
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except ImportError:
        return _redirect_with_error('python3-saml+not+installed')

    relay_state = request.form.get('RelayState', '')
    provider = _consume_state(relay_state)
    if provider != 'saml':
        return _redirect_with_error('Invalid+or+expired+SSO+state')

    try:
        saml_auth = OneLogin_Saml2_Auth(_saml_prepare_flask_request(request), _saml_settings())
        saml_auth.process_response()
    except Exception as exc:
        return _redirect_with_error(f'SAML+response+processing+failed: {exc}')

    if saml_auth.get_errors():
        return _redirect_with_error(saml_auth.get_last_error_reason() or 'SAML+validation+failed')
    if not saml_auth.is_authenticated():
        return _redirect_with_error('SAML+authentication+failed')

    email = (saml_auth.get_nameid() or '').lower().strip()
    if not email:
        attrs = saml_auth.get_attributes() or {}
        for key in ('email', 'mail', 'emailaddress',
                    'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'):
            if attrs.get(key):
                email = attrs[key][0].lower().strip()
                break

    if not email:
        return _redirect_with_error('No+email+returned+from+SAML+IdP')

    user = _find_or_create_user(email, 'saml')
    if not user:
        return _redirect_with_error('Account+not+found.+Contact+your+administrator.')

    audit.log_login(user.username, success=True, remote_addr=request.remote_addr or '')
    return _redirect_with_token(generate_token(user))


@bp.get('/auth/sso/saml/metadata')
def sso_saml_metadata():
    """SP metadata XML — paste this URL into the IdP (Okta/Azure AD/Ping) app config."""
    if not _saml_configured():
        return jsonify({'error': 'SAML SSO is not configured'}), 501
    try:
        from onelogin.saml2.settings import OneLogin_Saml2_Settings
    except ImportError:
        return jsonify({'error': 'python3-saml not installed'}), 501

    saml_settings = OneLogin_Saml2_Settings(settings=_saml_settings(), sp_validation_only=True)
    metadata = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata)
    if errors:
        return jsonify({'error': 'Invalid SP metadata', 'details': errors}), 500
    return Response(metadata, mimetype='text/xml')


# ── SSO config status (used by Login page to show/hide buttons) ───────────────

@bp.get('/auth/sso/providers')
def sso_providers():
    """Return which SSO providers are configured (no auth required — called from login page)."""
    return jsonify({
        'google':    _google_configured(),
        'microsoft': _microsoft_configured(),
        'saml':      _saml_configured(),
    })
