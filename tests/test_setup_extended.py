"""Tests for setup/status endpoints and auth refresh."""


# ── POST /auth/refresh ────────────────────────────────────────────────────────

def test_auth_refresh_returns_new_token(client, headers):
    resp = client.post('/api/auth/refresh', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'token' in data
    assert isinstance(data['token'], str)
    assert len(data['token']) > 10


def test_auth_refresh_new_token_is_valid(client, headers):
    """Token from /auth/refresh should work as auth for subsequent requests."""
    refresh_resp = client.post('/api/auth/refresh', headers=headers)
    new_token = refresh_resp.get_json()['token']
    new_headers = {'Authorization': f'Bearer {new_token}', 'Content-Type': 'application/json'}
    resp = client.get('/api/pipelines', headers=new_headers)
    assert resp.status_code == 200


def test_auth_refresh_requires_auth(client):
    resp = client.post('/api/auth/refresh')
    assert resp.status_code == 401


# ── GET /setup/status ─────────────────────────────────────────────────────────

def test_setup_status_returns_200(client, headers):
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200


def test_setup_status_has_expected_keys(client, headers):
    resp = client.get('/api/setup/status', headers=headers)
    data = resp.get_json()
    assert 'gmail' in data
    assert 'drive' in data
    assert 'microsoft365' in data
    assert 'ai' in data
    assert 'retention' in data


def test_setup_status_gmail_not_configured_by_default(client, headers, monkeypatch):
    monkeypatch.delenv('GMAIL_CLIENT_ID', raising=False)
    monkeypatch.delenv('GMAIL_CLIENT_SECRET', raising=False)
    monkeypatch.delenv('GMAIL_REFRESH_TOKEN', raising=False)
    monkeypatch.delenv('GMAIL_SENDER', raising=False)
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['gmail']['configured'] is False


def test_setup_status_gmail_configured_when_env_set(client, headers, monkeypatch):
    monkeypatch.setenv('GMAIL_CLIENT_ID', 'fake_id')
    monkeypatch.setenv('GMAIL_CLIENT_SECRET', 'fake_secret')
    monkeypatch.setenv('GMAIL_REFRESH_TOKEN', 'fake_token')
    monkeypatch.setenv('GMAIL_SENDER', 'sender@gmail.com')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['gmail']['configured'] is True


def test_setup_status_m365_not_configured_by_default(client, headers, monkeypatch):
    monkeypatch.delenv('MICROSOFT_TENANT_ID', raising=False)
    monkeypatch.delenv('MICROSOFT_CLIENT_ID', raising=False)
    monkeypatch.delenv('MICROSOFT_CLIENT_SECRET', raising=False)
    monkeypatch.delenv('MICROSOFT_SENDER_EMAIL', raising=False)
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['microsoft365']['configured'] is False


def test_setup_status_ai_enabled_by_default(client, headers, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_AI_ENABLED', raising=False)
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['ai']['enabled'] is True


def test_setup_status_ai_disabled(client, headers, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AI_ENABLED', 'false')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['ai']['enabled'] is False


def test_setup_status_retention_defaults(client, headers, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_RUN_RETENTION_DAYS', raising=False)
    monkeypatch.delenv('FLOWFORGE_AUDIT_RETENTION_DAYS', raising=False)
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200
    retention = resp.get_json()['retention']
    assert retention['run_days'] == 90
    assert retention['audit_days'] == 90


def test_setup_status_retention_custom(client, headers, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_RUN_RETENTION_DAYS', '30')
    monkeypatch.setenv('FLOWFORGE_AUDIT_RETENTION_DAYS', '60')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.status_code == 200
    retention = resp.get_json()['retention']
    assert retention['run_days'] == 30
    assert retention['audit_days'] == 60


def test_setup_status_ollama_url_in_response(client, headers, monkeypatch):
    monkeypatch.setenv('OLLAMA_URL', 'http://custom-ollama:11434')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.get_json()['ai']['ollama_url'] == 'http://custom-ollama:11434'


def test_setup_status_claude_not_configured_by_default(client, headers, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.get_json()['ai']['claude']['configured'] is False


def test_setup_status_claude_configured_when_env_set(client, headers, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.get_json()['ai']['claude']['configured'] is True


def test_setup_status_gemini_not_configured_by_default(client, headers, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.get_json()['ai']['gemini']['configured'] is False


def test_setup_status_gemini_configured_when_env_set(client, headers, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.get_json()['ai']['gemini']['configured'] is True


def test_setup_status_gemini_model_in_response(client, headers, monkeypatch):
    monkeypatch.setenv('GEMINI_QUERY_MODEL', 'gemini-2.5-pro')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.get_json()['ai']['gemini']['model'] == 'gemini-2.5-pro'


def test_setup_status_requires_auth(client):
    resp = client.get('/api/setup/status')
    assert resp.status_code == 401


def test_setup_status_drive_sender_in_response(client, headers, monkeypatch):
    monkeypatch.setenv('GMAIL_SENDER', 'test@gmail.com')
    resp = client.get('/api/setup/status', headers=headers)
    assert resp.get_json()['gmail']['sender'] == 'test@gmail.com'


# ── POST /setup/gmail ─────────────────────────────────────────────────────────

def test_setup_gmail_returns_200(client, headers):
    resp = client.post('/api/setup/gmail', headers=headers)
    assert resp.status_code == 200


def test_setup_gmail_returns_instruction_message(client, headers):
    resp = client.post('/api/setup/gmail', headers=headers)
    msg = resp.get_json().get('message', '')
    assert 'flowforge setup gmail' in msg


def test_setup_gmail_requires_auth(client):
    resp = client.post('/api/setup/gmail')
    assert resp.status_code == 401


# ── POST /setup/microsoft365 ──────────────────────────────────────────────────

def test_setup_microsoft365_returns_200(client, headers):
    resp = client.post('/api/setup/microsoft365', headers=headers)
    assert resp.status_code == 200


def test_setup_microsoft365_returns_instruction_message(client, headers):
    resp = client.post('/api/setup/microsoft365', headers=headers)
    msg = resp.get_json().get('message', '')
    assert 'microsoft365' in msg.lower() or 'flowforge setup' in msg


def test_setup_microsoft365_requires_auth(client):
    resp = client.post('/api/setup/microsoft365')
    assert resp.status_code == 401
