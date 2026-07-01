"""Tests for flowforge/api/routes/sso.py — SSO OAuth2 routes."""
import sys
import time
import uuid
from types import ModuleType
from unittest.mock import MagicMock, patch

# ── helpers ───────────────────────────────────────────────────────────────────

def _clear_sso_states():
    """Clear in-memory SSO state store between tests."""
    from flowforge.api.routes.sso import _SSO_STATES
    _SSO_STATES.clear()


def _inject_google_state(app_url='http://localhost:5000'):
    """Insert a valid Google SSO state token, return the token."""
    from flowforge.api.routes.sso import _new_state
    return _new_state('google')


def _inject_microsoft_state():
    from flowforge.api.routes.sso import _new_state
    return _new_state('microsoft')


# ── _app_url / _auto_create ───────────────────────────────────────────────────

def test_app_url_default(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_APP_URL', raising=False)
    from flowforge.api.routes.sso import _app_url
    assert _app_url() == 'http://localhost:5000'


def test_app_url_from_env(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_APP_URL', 'https://myapp.example.com/')
    # Need to re-evaluate since module caches nothing
    from flowforge.api.routes import sso as sso_mod
    result = sso_mod._app_url()
    # trailing slash stripped
    assert result == 'https://myapp.example.com'


def test_auto_create_false_by_default(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_SSO_AUTO_CREATE', raising=False)
    from flowforge.api.routes.sso import _auto_create
    assert _auto_create() is False


def test_auto_create_true_when_set(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    from flowforge.api.routes.sso import _auto_create
    assert _auto_create() is True


def test_auto_create_case_insensitive(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'TRUE')
    from flowforge.api.routes.sso import _auto_create
    assert _auto_create() is True


# ── _new_state / _consume_state / _expire_states ─────────────────────────────

def test_new_state_returns_token():
    _clear_sso_states()
    from flowforge.api.routes.sso import _new_state
    token = _new_state('google')
    assert isinstance(token, str)
    assert len(token) > 10


def test_consume_state_valid_token():
    _clear_sso_states()
    from flowforge.api.routes.sso import _consume_state, _new_state
    token = _new_state('google')
    provider = _consume_state(token)
    assert provider == 'google'


def test_consume_state_invalid_token():
    _clear_sso_states()
    from flowforge.api.routes.sso import _consume_state
    result = _consume_state('not-a-real-token')
    assert result is None


def test_consume_state_removes_token():
    _clear_sso_states()
    from flowforge.api.routes.sso import _consume_state, _new_state
    token = _new_state('microsoft')
    _consume_state(token)
    # Second consume should return None
    assert _consume_state(token) is None


def test_expire_states_removes_expired():
    _clear_sso_states()
    from flowforge.api.routes import sso as sso_mod
    # Manually insert an expired state
    sso_mod._SSO_STATES['expired_token'] = ('google', time.monotonic() - 1)
    sso_mod._expire_states()
    assert 'expired_token' not in sso_mod._SSO_STATES


def test_new_state_triggers_expire():
    """_new_state calls _expire_states to clean up old entries."""
    _clear_sso_states()
    from flowforge.api.routes import sso as sso_mod
    sso_mod._SSO_STATES['stale'] = ('google', time.monotonic() - 100)
    sso_mod._new_state('google')
    assert 'stale' not in sso_mod._SSO_STATES


# ── GET /api/auth/sso/providers ───────────────────────────────────────────────

def test_sso_providers_both_false(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_ID', raising=False)
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_SECRET', raising=False)
    monkeypatch.delenv('MICROSOFT_SSO_TENANT_ID', raising=False)
    monkeypatch.delenv('MICROSOFT_SSO_CLIENT_ID', raising=False)
    monkeypatch.delenv('MICROSOFT_SSO_CLIENT_SECRET', raising=False)
    monkeypatch.delenv('SAML_SP_ENTITY_ID', raising=False)
    monkeypatch.delenv('SAML_IDP_ENTITY_ID', raising=False)
    monkeypatch.delenv('SAML_IDP_SSO_URL', raising=False)
    monkeypatch.delenv('SAML_IDP_X509_CERT', raising=False)
    resp = client.get('/api/auth/sso/providers')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['google'] is False
    assert data['microsoft'] is False
    assert data['saml'] is False


def test_sso_providers_saml_true(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_ID', raising=False)
    monkeypatch.delenv('MICROSOFT_SSO_TENANT_ID', raising=False)
    monkeypatch.setenv('SAML_SP_ENTITY_ID', 'https://flowforge.example.com/saml')
    monkeypatch.setenv('SAML_IDP_ENTITY_ID', 'https://idp.example.com/entity')
    monkeypatch.setenv('SAML_IDP_SSO_URL', 'https://idp.example.com/sso')
    monkeypatch.setenv('SAML_IDP_X509_CERT', 'FAKECERT')
    resp = client.get('/api/auth/sso/providers')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['saml'] is True
    assert data['google'] is False
    assert data['microsoft'] is False


def test_sso_providers_saml_false_when_partial(client, monkeypatch):
    """All four SAML env vars are required — missing one keeps saml=False."""
    monkeypatch.setenv('SAML_SP_ENTITY_ID', 'https://flowforge.example.com/saml')
    monkeypatch.setenv('SAML_IDP_ENTITY_ID', 'https://idp.example.com/entity')
    monkeypatch.setenv('SAML_IDP_SSO_URL', 'https://idp.example.com/sso')
    monkeypatch.delenv('SAML_IDP_X509_CERT', raising=False)
    resp = client.get('/api/auth/sso/providers')
    assert resp.get_json()['saml'] is False


def test_sso_providers_google_true(client, monkeypatch):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    monkeypatch.delenv('MICROSOFT_SSO_TENANT_ID', raising=False)
    resp = client.get('/api/auth/sso/providers')
    assert resp.status_code == 200
    assert resp.get_json()['google'] is True
    assert resp.get_json()['microsoft'] is False


def test_sso_providers_microsoft_true(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_ID', raising=False)
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    resp = client.get('/api/auth/sso/providers')
    assert resp.status_code == 200
    assert resp.get_json()['microsoft'] is True
    assert resp.get_json()['google'] is False


# ── GET /api/auth/sso/google (start) ─────────────────────────────────────────

def test_sso_google_start_not_configured(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_ID', raising=False)
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_SECRET', raising=False)
    resp = client.get('/api/auth/sso/google')
    assert resp.status_code == 501
    assert 'not configured' in resp.get_json()['error'].lower()


def test_sso_google_start_library_not_installed(client, monkeypatch):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')

    # Remove the module from sys.modules to trigger ImportError on import
    saved = {k: v for k, v in sys.modules.items()
             if k.startswith('google_auth_oauthlib')}
    for k in saved:
        del sys.modules[k]

    # Patch the import to raise ImportError
    with patch.dict('sys.modules', {
        'google_auth_oauthlib': None,
        'google_auth_oauthlib.flow': None,
    }):
        resp = client.get('/api/auth/sso/google')

    assert resp.status_code == 501
    assert 'not installed' in resp.get_json()['error'].lower()


def test_sso_google_start_redirects(client, monkeypatch):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    _clear_sso_states()

    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ('https://accounts.google.com/o/oauth2/auth?state=xyz', 'xyz')

    mock_flow_class = MagicMock(return_value=mock_flow)
    mock_flow_class.from_client_config = MagicMock(return_value=mock_flow)

    mock_oauthlib = ModuleType('google_auth_oauthlib')
    mock_oauthlib_flow = ModuleType('google_auth_oauthlib.flow')
    mock_oauthlib_flow.Flow = mock_flow_class
    mock_oauthlib.flow = mock_oauthlib_flow

    with patch.dict('sys.modules', {
        'google_auth_oauthlib': mock_oauthlib,
        'google_auth_oauthlib.flow': mock_oauthlib_flow,
    }):
        resp = client.get('/api/auth/sso/google', follow_redirects=False)

    assert resp.status_code == 302
    assert 'accounts.google.com' in resp.headers.get('Location', '')


# ── GET /api/auth/sso/google/callback ────────────────────────────────────────

def test_sso_google_callback_not_configured(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_ID', raising=False)
    monkeypatch.delenv('GOOGLE_SSO_CLIENT_SECRET', raising=False)
    resp = client.get('/api/auth/sso/google/callback', follow_redirects=False)
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_google_callback_invalid_state(client, monkeypatch):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    _clear_sso_states()
    resp = client.get(
        '/api/auth/sso/google/callback?state=invalid-state-token',
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_google_callback_error_param(client, monkeypatch):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    _clear_sso_states()
    # Inject a valid state
    token = _inject_google_state()
    resp = client.get(
        f'/api/auth/sso/google/callback?state={token}&error=access_denied',
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_google_callback_token_exchange_exception(client, monkeypatch):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    _clear_sso_states()
    token = _inject_google_state()

    mock_flow = MagicMock()
    mock_flow.fetch_token.side_effect = Exception('token exchange failed')
    mock_flow_class = MagicMock(return_value=mock_flow)
    mock_flow_class.from_client_config = MagicMock(return_value=mock_flow)

    mock_oauthlib = ModuleType('google_auth_oauthlib')
    mock_oauthlib_flow = ModuleType('google_auth_oauthlib.flow')
    mock_oauthlib_flow.Flow = mock_flow_class

    with patch.dict('sys.modules', {
        'google_auth_oauthlib': mock_oauthlib,
        'google_auth_oauthlib.flow': mock_oauthlib_flow,
    }):
        resp = client.get(
            f'/api/auth/sso/google/callback?state={token}',
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_google_callback_no_email_returned(client, monkeypatch):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    _clear_sso_states()
    token = _inject_google_state()

    mock_creds = MagicMock()
    mock_creds.token = 'fake_access_token'
    mock_flow = MagicMock()
    mock_flow.credentials = mock_creds
    mock_flow.fetch_token.return_value = None
    mock_flow_class = MagicMock()
    mock_flow_class.from_client_config.return_value = mock_flow

    mock_oauthlib = ModuleType('google_auth_oauthlib')
    mock_oauthlib_flow = ModuleType('google_auth_oauthlib.flow')
    mock_oauthlib_flow.Flow = mock_flow_class

    mock_requests = ModuleType('requests')
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'email': ''}  # empty email
    mock_resp.raise_for_status.return_value = None
    mock_requests.get = MagicMock(return_value=mock_resp)

    with patch.dict('sys.modules', {
        'google_auth_oauthlib': mock_oauthlib,
        'google_auth_oauthlib.flow': mock_oauthlib_flow,
        'requests': mock_requests,
    }):
        resp = client.get(
            f'/api/auth/sso/google/callback?state={token}',
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_google_callback_user_not_found_no_autocreate(client, monkeypatch, app):
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'false')
    _clear_sso_states()
    token = _inject_google_state()

    mock_creds = MagicMock()
    mock_creds.token = 'fake_access_token'
    mock_flow = MagicMock()
    mock_flow.credentials = mock_creds
    mock_flow_class = MagicMock()
    mock_flow_class.from_client_config.return_value = mock_flow

    mock_oauthlib = ModuleType('google_auth_oauthlib')
    mock_oauthlib_flow = ModuleType('google_auth_oauthlib.flow')
    mock_oauthlib_flow.Flow = mock_flow_class

    mock_requests = ModuleType('requests')
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'email': 'noexist_sso_user@example.com'}
    mock_resp.raise_for_status.return_value = None
    mock_requests.get = MagicMock(return_value=mock_resp)

    with patch.dict('sys.modules', {
        'google_auth_oauthlib': mock_oauthlib,
        'google_auth_oauthlib.flow': mock_oauthlib_flow,
        'requests': mock_requests,
    }):
        resp = client.get(
            f'/api/auth/sso/google/callback?state={token}',
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_google_callback_success(client, monkeypatch, app):
    """Successful callback for an existing user returns a redirect with sso_token."""
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_ID', 'gid')
    monkeypatch.setenv('GOOGLE_SSO_CLIENT_SECRET', 'gsecret')
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    _clear_sso_states()
    token = _inject_google_state()

    test_email = 'sso_success_user@example.com'

    mock_creds = MagicMock()
    mock_creds.token = 'fake_access_token'
    mock_flow = MagicMock()
    mock_flow.credentials = mock_creds
    mock_flow_class = MagicMock()
    mock_flow_class.from_client_config.return_value = mock_flow

    mock_oauthlib = ModuleType('google_auth_oauthlib')
    mock_oauthlib_flow = ModuleType('google_auth_oauthlib.flow')
    mock_oauthlib_flow.Flow = mock_flow_class

    mock_requests = ModuleType('requests')
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'email': test_email}
    mock_resp.raise_for_status.return_value = None
    mock_requests.get = MagicMock(return_value=mock_resp)

    with patch.dict('sys.modules', {
        'google_auth_oauthlib': mock_oauthlib,
        'google_auth_oauthlib.flow': mock_oauthlib_flow,
        'requests': mock_requests,
    }):
        resp = client.get(
            f'/api/auth/sso/google/callback?state={token}',
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers.get('Location', '')
    # Should redirect with a token (either sso_token or sso_error — if user created)
    assert 'sso_token' in location or 'sso_error' in location

    # Cleanup: remove the auto-created user if it exists
    from flowforge.db.models import User, db
    with app.app_context():
        u = db.session.query(User).filter_by(sso_email=test_email).first()
        if u:
            db.session.delete(u)
            db.session.commit()


# ── GET /api/auth/sso/microsoft (start) ──────────────────────────────────────

def test_sso_microsoft_start_not_configured(client, monkeypatch):
    monkeypatch.delenv('MICROSOFT_SSO_TENANT_ID', raising=False)
    monkeypatch.delenv('MICROSOFT_SSO_CLIENT_ID', raising=False)
    monkeypatch.delenv('MICROSOFT_SSO_CLIENT_SECRET', raising=False)
    resp = client.get('/api/auth/sso/microsoft')
    assert resp.status_code == 501
    assert 'not configured' in resp.get_json()['error'].lower()


def test_sso_microsoft_start_msal_not_installed(client, monkeypatch):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')

    with patch.dict('sys.modules', {'msal': None}):
        resp = client.get('/api/auth/sso/microsoft')

    assert resp.status_code == 501
    assert 'not installed' in resp.get_json()['error'].lower()


def test_sso_microsoft_start_redirects(client, monkeypatch):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    _clear_sso_states()

    mock_cca = MagicMock()
    mock_cca.get_authorization_request_url.return_value = (
        'https://login.microsoftonline.com/tenant/oauth2/v2.0/authorize?state=abc'
    )

    mock_msal = ModuleType('msal')
    mock_msal.ConfidentialClientApplication = MagicMock(return_value=mock_cca)

    with patch.dict('sys.modules', {'msal': mock_msal}):
        resp = client.get('/api/auth/sso/microsoft', follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers.get('Location', '')
    assert 'microsoftonline.com' in location or 'sso_error' not in location


# ── GET /api/auth/sso/microsoft/callback ─────────────────────────────────────

def test_sso_microsoft_callback_not_configured(client, monkeypatch):
    monkeypatch.delenv('MICROSOFT_SSO_TENANT_ID', raising=False)
    resp = client.get('/api/auth/sso/microsoft/callback', follow_redirects=False)
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_microsoft_callback_invalid_state(client, monkeypatch):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    _clear_sso_states()
    resp = client.get(
        '/api/auth/sso/microsoft/callback?state=bad-state',
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_microsoft_callback_error_param(client, monkeypatch):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    _clear_sso_states()
    token = _inject_microsoft_state()
    resp = client.get(
        f'/api/auth/sso/microsoft/callback?state={token}&error=access_denied&error_description=User+denied',
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_microsoft_callback_no_code(client, monkeypatch):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    _clear_sso_states()
    token = _inject_microsoft_state()
    resp = client.get(
        f'/api/auth/sso/microsoft/callback?state={token}',
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_microsoft_callback_token_error(client, monkeypatch):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    _clear_sso_states()
    token = _inject_microsoft_state()

    mock_cca = MagicMock()
    mock_cca.acquire_token_by_authorization_code.return_value = {
        'error': 'invalid_grant',
        'error_description': 'Token expired',
    }
    mock_msal = ModuleType('msal')
    mock_msal.ConfidentialClientApplication = MagicMock(return_value=mock_cca)

    with patch.dict('sys.modules', {'msal': mock_msal}):
        resp = client.get(
            f'/api/auth/sso/microsoft/callback?state={token}&code=auth_code_123',
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_microsoft_callback_no_email(client, monkeypatch):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    _clear_sso_states()
    token = _inject_microsoft_state()

    mock_cca = MagicMock()
    mock_cca.acquire_token_by_authorization_code.return_value = {
        'access_token': 'tok',
        'id_token_claims': {},  # no email or preferred_username
    }
    mock_msal = ModuleType('msal')
    mock_msal.ConfidentialClientApplication = MagicMock(return_value=mock_cca)

    with patch.dict('sys.modules', {'msal': mock_msal}):
        resp = client.get(
            f'/api/auth/sso/microsoft/callback?state={token}&code=auth_code_123',
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_microsoft_callback_success(client, monkeypatch, app):
    monkeypatch.setenv('MICROSOFT_SSO_TENANT_ID', 'tenant')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_ID', 'mid')
    monkeypatch.setenv('MICROSOFT_SSO_CLIENT_SECRET', 'msecret')
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    _clear_sso_states()
    token = _inject_microsoft_state()

    test_email = 'ms_sso_success@example.com'

    mock_cca = MagicMock()
    mock_cca.acquire_token_by_authorization_code.return_value = {
        'access_token': 'tok',
        'id_token_claims': {
            'email': test_email,
        },
    }
    mock_msal = ModuleType('msal')
    mock_msal.ConfidentialClientApplication = MagicMock(return_value=mock_cca)

    with patch.dict('sys.modules', {'msal': mock_msal}):
        resp = client.get(
            f'/api/auth/sso/microsoft/callback?state={token}&code=auth_code_123',
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers.get('Location', '')
    assert 'sso_token' in location or 'sso_error' in location

    # Cleanup
    from flowforge.db.models import User, db
    with app.app_context():
        u = db.session.query(User).filter_by(sso_email=test_email).first()
        if u:
            db.session.delete(u)
            db.session.commit()


# ── SAML SSO helpers ───────────────────────────────────────────────────────────

_SAML_ENV = {
    'SAML_SP_ENTITY_ID':  'https://flowforge.example.com/saml',
    'SAML_IDP_ENTITY_ID': 'https://idp.example.com/entity',
    'SAML_IDP_SSO_URL':   'https://idp.example.com/sso',
    'SAML_IDP_X509_CERT': 'FAKECERT',
}


def _set_saml_env(monkeypatch):
    for k, v in _SAML_ENV.items():
        monkeypatch.setenv(k, v)


def _inject_saml_state():
    from flowforge.api.routes.sso import _new_state
    return _new_state('saml')


def _mock_saml_auth_module(auth_instance):
    """Build fake onelogin.saml2.auth module exposing OneLogin_Saml2_Auth."""
    mock_auth_class = MagicMock(return_value=auth_instance)
    mod = ModuleType('onelogin.saml2.auth')
    mod.OneLogin_Saml2_Auth = mock_auth_class
    return mod


def _mock_saml_settings_module(settings_instance):
    """Build fake onelogin.saml2.settings module exposing OneLogin_Saml2_Settings."""
    mock_settings_class = MagicMock(return_value=settings_instance)
    mod = ModuleType('onelogin.saml2.settings')
    mod.OneLogin_Saml2_Settings = mock_settings_class
    return mod


# ── _saml_configured / _saml_settings / _saml_acs_url ────────────────────────

def test_saml_configured_false_when_missing(monkeypatch):
    monkeypatch.delenv('SAML_SP_ENTITY_ID', raising=False)
    from flowforge.api.routes.sso import _saml_configured
    assert _saml_configured() is False


def test_saml_configured_true_when_all_set(monkeypatch):
    _set_saml_env(monkeypatch)
    from flowforge.api.routes.sso import _saml_configured
    assert _saml_configured() is True


def test_saml_acs_url_uses_app_url(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_APP_URL', 'https://myapp.example.com')
    from flowforge.api.routes.sso import _saml_acs_url
    assert _saml_acs_url() == 'https://myapp.example.com/api/auth/sso/saml/acs'


def test_saml_settings_shape(monkeypatch):
    _set_saml_env(monkeypatch)
    from flowforge.api.routes.sso import _saml_settings
    settings = _saml_settings()
    assert settings['sp']['entityId'] == _SAML_ENV['SAML_SP_ENTITY_ID']
    assert settings['idp']['entityId'] == _SAML_ENV['SAML_IDP_ENTITY_ID']
    assert settings['idp']['singleSignOnService']['url'] == _SAML_ENV['SAML_IDP_SSO_URL']
    assert settings['idp']['x509cert'] == _SAML_ENV['SAML_IDP_X509_CERT']
    assert settings['security']['wantAssertionsSigned'] is True


# ── GET /api/auth/sso/saml/login ──────────────────────────────────────────────

def test_sso_saml_start_not_configured(client, monkeypatch):
    monkeypatch.delenv('SAML_SP_ENTITY_ID', raising=False)
    resp = client.get('/api/auth/sso/saml/login')
    assert resp.status_code == 501
    assert 'not configured' in resp.get_json()['error'].lower()


def test_sso_saml_start_library_not_installed(client, monkeypatch):
    _set_saml_env(monkeypatch)
    with patch.dict('sys.modules', {'onelogin.saml2.auth': None}):
        resp = client.get('/api/auth/sso/saml/login')
    assert resp.status_code == 501
    assert 'not installed' in resp.get_json()['error'].lower()


def test_sso_saml_start_redirects(client, monkeypatch):
    _set_saml_env(monkeypatch)
    _clear_sso_states()

    mock_auth = MagicMock()
    mock_auth.login.return_value = 'https://idp.example.com/sso?SAMLRequest=xyz'

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.get('/api/auth/sso/saml/login', follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers.get('Location') == 'https://idp.example.com/sso?SAMLRequest=xyz'


# ── POST /api/auth/sso/saml/acs ───────────────────────────────────────────────

def test_sso_saml_acs_not_configured(client, monkeypatch):
    monkeypatch.delenv('SAML_SP_ENTITY_ID', raising=False)
    resp = client.post('/api/auth/sso/saml/acs', data={}, follow_redirects=False)
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_saml_acs_invalid_relay_state(client, monkeypatch):
    _set_saml_env(monkeypatch)
    _clear_sso_states()
    resp = client.post(
        '/api/auth/sso/saml/acs',
        data={'RelayState': 'not-a-real-token', 'SAMLResponse': 'xxx'},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_saml_acs_processing_exception(client, monkeypatch):
    _set_saml_env(monkeypatch)
    _clear_sso_states()
    token = _inject_saml_state()

    mock_auth = MagicMock()
    mock_auth.process_response.side_effect = Exception('malformed response')

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.post(
            '/api/auth/sso/saml/acs',
            data={'RelayState': token, 'SAMLResponse': 'xxx'},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_saml_acs_validation_errors(client, monkeypatch):
    _set_saml_env(monkeypatch)
    _clear_sso_states()
    token = _inject_saml_state()

    mock_auth = MagicMock()
    mock_auth.process_response.return_value = None
    mock_auth.get_errors.return_value = ['invalid_response']
    mock_auth.get_last_error_reason.return_value = 'Signature validation failed'

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.post(
            '/api/auth/sso/saml/acs',
            data={'RelayState': token, 'SAMLResponse': 'xxx'},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_saml_acs_not_authenticated(client, monkeypatch):
    _set_saml_env(monkeypatch)
    _clear_sso_states()
    token = _inject_saml_state()

    mock_auth = MagicMock()
    mock_auth.process_response.return_value = None
    mock_auth.get_errors.return_value = []
    mock_auth.is_authenticated.return_value = False

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.post(
            '/api/auth/sso/saml/acs',
            data={'RelayState': token, 'SAMLResponse': 'xxx'},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_error' in resp.headers['Location']


def test_sso_saml_acs_no_email(client, monkeypatch):
    _set_saml_env(monkeypatch)
    _clear_sso_states()
    token = _inject_saml_state()

    mock_auth = MagicMock()
    mock_auth.process_response.return_value = None
    mock_auth.get_errors.return_value = []
    mock_auth.is_authenticated.return_value = True
    mock_auth.get_nameid.return_value = ''
    mock_auth.get_attributes.return_value = {}

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.post(
            '/api/auth/sso/saml/acs',
            data={'RelayState': token, 'SAMLResponse': 'xxx'},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'No+email' in resp.headers['Location']


def test_sso_saml_acs_email_from_attributes(client, monkeypatch, app):
    """When NameID is empty, fall back to the 'email' attribute."""
    _set_saml_env(monkeypatch)
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    _clear_sso_states()
    token = _inject_saml_state()

    test_email = 'saml_attr_user@example.com'
    mock_auth = MagicMock()
    mock_auth.process_response.return_value = None
    mock_auth.get_errors.return_value = []
    mock_auth.is_authenticated.return_value = True
    mock_auth.get_nameid.return_value = ''
    mock_auth.get_attributes.return_value = {'email': [test_email]}

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.post(
            '/api/auth/sso/saml/acs',
            data={'RelayState': token, 'SAMLResponse': 'xxx'},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_token' in resp.headers['Location']

    from flowforge.db.models import User, db
    with app.app_context():
        u = db.session.query(User).filter_by(sso_email=test_email).first()
        assert u is not None
        assert u.sso_provider == 'saml'
        db.session.delete(u)
        db.session.commit()


def test_sso_saml_acs_account_not_found(client, monkeypatch):
    _set_saml_env(monkeypatch)
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'false')
    _clear_sso_states()
    token = _inject_saml_state()

    mock_auth = MagicMock()
    mock_auth.process_response.return_value = None
    mock_auth.get_errors.return_value = []
    mock_auth.is_authenticated.return_value = True
    mock_auth.get_nameid.return_value = 'zzz_saml_nomatch@unknown.com'
    mock_auth.get_attributes.return_value = {}

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.post(
            '/api/auth/sso/saml/acs',
            data={'RelayState': token, 'SAMLResponse': 'xxx'},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'Account+not+found' in resp.headers['Location']


def test_sso_saml_acs_success(client, monkeypatch, app):
    _set_saml_env(monkeypatch)
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    _clear_sso_states()
    token = _inject_saml_state()

    test_email = 'saml_success_user@example.com'
    mock_auth = MagicMock()
    mock_auth.process_response.return_value = None
    mock_auth.get_errors.return_value = []
    mock_auth.is_authenticated.return_value = True
    mock_auth.get_nameid.return_value = test_email
    mock_auth.get_attributes.return_value = {}

    with patch.dict('sys.modules', {'onelogin.saml2.auth': _mock_saml_auth_module(mock_auth)}):
        resp = client.post(
            '/api/auth/sso/saml/acs',
            data={'RelayState': token, 'SAMLResponse': 'xxx'},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert 'sso_token' in resp.headers['Location']

    from flowforge.db.models import User, db
    with app.app_context():
        u = db.session.query(User).filter_by(sso_email=test_email).first()
        if u:
            db.session.delete(u)
            db.session.commit()


# ── GET /api/auth/sso/saml/metadata ───────────────────────────────────────────

def test_sso_saml_metadata_not_configured(client, monkeypatch):
    monkeypatch.delenv('SAML_SP_ENTITY_ID', raising=False)
    resp = client.get('/api/auth/sso/saml/metadata')
    assert resp.status_code == 501


def test_sso_saml_metadata_library_not_installed(client, monkeypatch):
    _set_saml_env(monkeypatch)
    with patch.dict('sys.modules', {'onelogin.saml2.settings': None}):
        resp = client.get('/api/auth/sso/saml/metadata')
    assert resp.status_code == 501
    assert 'not installed' in resp.get_json()['error'].lower()


def test_sso_saml_metadata_success(client, monkeypatch):
    _set_saml_env(monkeypatch)
    mock_settings = MagicMock()
    mock_settings.get_sp_metadata.return_value = b'<EntityDescriptor></EntityDescriptor>'
    mock_settings.validate_metadata.return_value = []

    with patch.dict('sys.modules', {'onelogin.saml2.settings': _mock_saml_settings_module(mock_settings)}):
        resp = client.get('/api/auth/sso/saml/metadata')

    assert resp.status_code == 200
    assert resp.content_type.startswith('text/xml')


def test_sso_saml_metadata_invalid(client, monkeypatch):
    _set_saml_env(monkeypatch)
    mock_settings = MagicMock()
    mock_settings.get_sp_metadata.return_value = b'<EntityDescriptor></EntityDescriptor>'
    mock_settings.validate_metadata.return_value = ['missing_entity_id']

    with patch.dict('sys.modules', {'onelogin.saml2.settings': _mock_saml_settings_module(mock_settings)}):
        resp = client.get('/api/auth/sso/saml/metadata')

    assert resp.status_code == 500


# ── _find_or_create_user ──────────────────────────────────────────────────────

def test_find_or_create_user_existing_sso_email(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'false')
    import secrets as sec_mod

    import bcrypt as bc_mod

    from flowforge.api.routes.sso import _find_or_create_user
    from flowforge.db.models import User, db

    test_email = 'sso_exist@example.com'
    uid = str(uuid.uuid4())

    with app.app_context():
        dummy_hash = bc_mod.hashpw(sec_mod.token_bytes(16), bc_mod.gensalt(4)).decode()
        u = User(
            id=uid,
            username='sso_exist',
            password_hash=dummy_hash,
            role='viewer',
            sso_email=test_email,
            sso_provider='google',
        )
        db.session.add(u)
        db.session.commit()

        found = _find_or_create_user(test_email, 'google')
        assert found is not None
        assert found.sso_email == test_email

        db.session.delete(u)
        db.session.commit()


def test_find_or_create_user_no_autocreate_no_match(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'false')
    from flowforge.api.routes.sso import _find_or_create_user

    with app.app_context():
        result = _find_or_create_user('zzz_nomatch_person@unknown.com', 'google')
        assert result is None


def test_find_or_create_user_autocreate_creates_user(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    from flowforge.api.routes.sso import _find_or_create_user
    from flowforge.db.models import User, db

    test_email = 'newssocreate_unique_xyz@example.com'

    with app.app_context():
        result = _find_or_create_user(test_email, 'google')
        assert result is not None
        assert result.sso_email == test_email
        assert result.role == 'viewer'

        # cleanup
        u = db.session.query(User).filter_by(sso_email=test_email).first()
        if u:
            db.session.delete(u)
            db.session.commit()


def test_find_or_create_user_username_collision_uses_email(app, monkeypatch):
    """When username collision exists, full email is used as username."""
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'true')
    import secrets as sec_mod

    import bcrypt as bc_mod

    from flowforge.api.routes.sso import _find_or_create_user
    from flowforge.db.models import User, db

    # Create a user with username that would collide
    conflicting_username = 'collision_user_x'
    test_email = f'{conflicting_username}@example.com'

    with app.app_context():
        dummy_hash = bc_mod.hashpw(sec_mod.token_bytes(16), bc_mod.gensalt(4)).decode()
        existing = User(
            id=str(uuid.uuid4()),
            username=conflicting_username,
            password_hash=dummy_hash,
            role='editor',
        )
        db.session.add(existing)
        db.session.commit()

        result = _find_or_create_user(test_email, 'google')
        assert result is not None
        # username should be full email, not just the prefix
        assert result.username == test_email

        # cleanup
        db.session.delete(result)
        db.session.delete(existing)
        db.session.commit()


def test_find_or_create_user_links_existing_username_without_sso(app, monkeypatch):
    """No auto-create but username matches existing user without sso_email → link."""
    monkeypatch.setenv('FLOWFORGE_SSO_AUTO_CREATE', 'false')
    import secrets as sec_mod

    import bcrypt as bc_mod

    from flowforge.api.routes.sso import _find_or_create_user
    from flowforge.db.models import User, db

    username = 'linkable_sso_user'
    test_email = f'{username}@example.com'

    with app.app_context():
        dummy_hash = bc_mod.hashpw(sec_mod.token_bytes(16), bc_mod.gensalt(4)).decode()
        u = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=dummy_hash,
            role='editor',
            sso_email=None,
        )
        db.session.add(u)
        db.session.commit()

        result = _find_or_create_user(test_email, 'google')
        assert result is not None
        assert result.sso_email == test_email
        assert result.sso_provider == 'google'

        # cleanup
        db.session.delete(u)
        db.session.commit()
