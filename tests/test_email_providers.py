"""Tests for email provider CRUD (/api/email-providers) and mocked send."""
from unittest.mock import MagicMock, patch

import pytest

SMTP_PAYLOAD = {
    'name': 'Test SMTP',
    'provider_type': 'smtp',
    'config': {
        'host': 'smtp.example.com',
        'port': 587,
        'username': 'sender@example.com',
        'password': 'secret123',
        'use_tls': True,
    },
}


@pytest.fixture
def provider_id(client, headers):
    resp = client.post('/api/email-providers', json=SMTP_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/email-providers/{pid}', headers=headers)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_list_providers(client, headers):
    resp = client.get('/api/email-providers', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_smtp_provider(client, headers):
    resp = client.post('/api/email-providers', json=SMTP_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test SMTP'
    assert data['provider_type'] == 'smtp'
    assert 'id' in data
    client.delete(f'/api/email-providers/{data["id"]}', headers=headers)


def test_create_provider_missing_name(client, headers):
    bad = {**SMTP_PAYLOAD}
    del bad['name']
    resp = client.post('/api/email-providers', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_provider_invalid_type(client, headers):
    bad = {**SMTP_PAYLOAD, 'provider_type': 'fax_machine'}
    resp = client.post('/api/email-providers', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_provider_missing_config(client, headers):
    bad = {k: v for k, v in SMTP_PAYLOAD.items() if k != 'config'}
    resp = client.post('/api/email-providers', json=bad, headers=headers)
    assert resp.status_code == 400


def test_get_provider(client, headers, provider_id):
    resp = client.get(f'/api/email-providers/{provider_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == provider_id
    assert data['provider_type'] == 'smtp'


def test_get_provider_config_returned(client, headers, provider_id):
    resp = client.get(f'/api/email-providers/{provider_id}', headers=headers)
    data = resp.get_json()
    assert 'config' in data
    assert data['config']['host'] == 'smtp.example.com'


def test_sensitive_fields_masked(client, headers, provider_id):
    resp = client.get(f'/api/email-providers/{provider_id}', headers=headers)
    cfg = resp.get_json()['config']
    assert cfg.get('password') == '***'


def test_update_provider_name(client, headers, provider_id):
    resp = client.put(f'/api/email-providers/{provider_id}',
                      json={'name': 'Updated SMTP'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Updated SMTP'


def test_update_provider_config_partial(client, headers, provider_id):
    resp = client.put(f'/api/email-providers/{provider_id}',
                      json={'config': {'host': 'new.smtp.com'}}, headers=headers)
    assert resp.status_code == 200
    cfg = resp.get_json()['config']
    assert cfg['host'] == 'new.smtp.com'
    assert cfg['port'] == 587


def test_update_config_masked_value_unchanged(client, headers, provider_id):
    """Sending *** back for a masked field must not overwrite the real value."""
    resp = client.put(f'/api/email-providers/{provider_id}',
                      json={'config': {'password': '***'}}, headers=headers)
    assert resp.status_code == 200
    # The actual password in DB stays as 'secret123' — verify by round-tripping
    after = client.get(f'/api/email-providers/{provider_id}', headers=headers).get_json()
    assert after['config']['password'] == '***'   # still masked, not blank


def test_delete_provider(client, headers):
    resp = client.post('/api/email-providers', json=SMTP_PAYLOAD, headers=headers)
    pid = resp.get_json()['id']
    assert client.delete(f'/api/email-providers/{pid}', headers=headers).status_code == 200
    assert client.get(f'/api/email-providers/{pid}', headers=headers).status_code == 404


def test_get_nonexistent_provider(client, headers):
    resp = client.get('/api/email-providers/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404


# ── Provider type variants ────────────────────────────────────────────────────

def test_create_gmail_provider(client, headers):
    payload = {
        'name': 'Gmail Test',
        'provider_type': 'gmail',
        'config': {
            'client_id': 'abc.apps.googleusercontent.com',
            'client_secret': 'secret',
            'refresh_token': 'refresh_abc',
            'sender': 'me@gmail.com',
        },
    }
    resp = client.post('/api/email-providers', json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['provider_type'] == 'gmail'
    client.delete(f'/api/email-providers/{data["id"]}', headers=headers)


def test_create_microsoft365_provider(client, headers):
    payload = {
        'name': 'M365 Test',
        'provider_type': 'microsoft365',
        'config': {
            'tenant_id': 'tenant-uuid',
            'client_id': 'client-uuid',
            'client_secret': 'secret',
            'sender_email': 'reports@company.com',
        },
    }
    resp = client.post('/api/email-providers', json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['provider_type'] == 'microsoft365'
    client.delete(f'/api/email-providers/{data["id"]}', headers=headers)


# ── SMTPProvider unit tests (no network) ─────────────────────────────────────

def test_smtp_send_success(tmp_path):
    from flowforge.email_providers.smtp import SMTPProvider

    provider = SMTPProvider(
        host='smtp.example.com', port=587,
        username='sender@example.com', password='pass',
        use_tls=True,
    )

    mock_server = MagicMock()
    with patch('smtplib.SMTP', return_value=mock_server):
        result = provider.send(
            to=['a@example.com'],
            cc=[], bcc=[],
            subject='Test',
            html_body='<p>Hello</p>',
            attachments=[],
        )

    assert result.success is True
    assert 'a@example.com' in result.recipients
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with('sender@example.com', 'pass')
    mock_server.send_message.assert_called_once()


def test_smtp_send_with_attachment(tmp_path):
    from flowforge.email_providers.smtp import SMTPProvider

    attachment = tmp_path / 'report.csv'
    attachment.write_text('col1,col2\n1,2\n')

    provider = SMTPProvider('smtp.example.com', 587, 'u', 'p', use_tls=False)
    mock_server = MagicMock()

    with patch('smtplib.SMTP', return_value=mock_server):
        result = provider.send(
            to=['r@example.com'], cc=[], bcc=[],
            subject='S', html_body='B',
            attachments=[attachment],
        )

    assert result.success is True
    mock_server.send_message.assert_called_once()


def test_smtp_send_failure_returns_error():
    from flowforge.email_providers.smtp import SMTPProvider

    provider = SMTPProvider('smtp.example.com', 587, 'u', 'p')
    mock_server = MagicMock()
    mock_server.starttls.side_effect = Exception('TLS failed')

    with patch('smtplib.SMTP', return_value=mock_server):
        result = provider.send(
            to=['r@example.com'], cc=[], bcc=[],
            subject='S', html_body='B', attachments=[],
        )

    assert result.success is False
    assert 'TLS failed' in result.error


def test_smtp_ssl_uses_smtp_ssl():
    from flowforge.email_providers.smtp import SMTPProvider

    provider = SMTPProvider('smtp.example.com', 465, 'u', 'p', use_ssl=True)
    mock_server = MagicMock()

    with patch('smtplib.SMTP_SSL', return_value=mock_server) as mock_ssl, \
         patch('smtplib.SMTP') as mock_plain:
        _ = provider.send([], [], [], 'S', 'B', [])

    mock_ssl.assert_called_once()
    mock_plain.assert_not_called()


def test_smtp_cc_bcc_included_in_recipients():
    from flowforge.email_providers.smtp import SMTPProvider

    provider = SMTPProvider('smtp.example.com', 587, 'u', 'p', use_tls=False)
    mock_server = MagicMock()

    with patch('smtplib.SMTP', return_value=mock_server):
        result = provider.send(
            to=['a@x.com'],
            cc=['b@x.com'],
            bcc=['c@x.com'],
            subject='S', html_body='B', attachments=[],
        )

    assert set(result.recipients) == {'a@x.com', 'b@x.com', 'c@x.com'}


# ── SMTP timeout on send() (NEW-2) ────────────────────────────────────────────

def test_smtp_send_passes_timeout_to_constructor():
    """send() must pass timeout=30 to SMTP() so blocked connections don't hang threads."""
    from flowforge.email_providers.smtp import SMTPProvider

    provider = SMTPProvider('smtp.example.com', 587, 'u', 'p', use_tls=False)
    mock_server = MagicMock()

    with patch('smtplib.SMTP', return_value=mock_server) as mock_smtp:
        provider.send(to=['r@example.com'], cc=[], bcc=[],
                      subject='S', html_body='B', attachments=[])

    _, kwargs = mock_smtp.call_args
    assert kwargs.get('timeout') == 30, (
        'smtplib.SMTP was not called with timeout=30 — slow servers will block pipeline threads'
    )


def test_smtp_ssl_send_passes_timeout_to_constructor():
    """send() with use_ssl=True must pass timeout=30 to SMTP_SSL()."""
    from flowforge.email_providers.smtp import SMTPProvider

    provider = SMTPProvider('smtp.example.com', 465, 'u', 'p', use_ssl=True)
    mock_server = MagicMock()

    with patch('smtplib.SMTP_SSL', return_value=mock_server) as mock_smtp_ssl:
        provider.send(to=['r@example.com'], cc=[], bcc=[],
                      subject='S', html_body='B', attachments=[])

    _, kwargs = mock_smtp_ssl.call_args
    assert kwargs.get('timeout') == 30, (
        'smtplib.SMTP_SSL was not called with timeout=30'
    )
