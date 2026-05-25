"""Unit tests for GmailProvider, Microsoft365Provider, and factory.get_email_provider.

All external I/O (Google APIs, MSAL, requests) is mocked so these tests run
without any cloud credentials or installed optional extras.
"""
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch, PropertyMock


# ─── helpers to inject fake modules so optional imports don't fail ────────────

def _make_google_mocks():
    """Return a minimal set of mock modules for google-auth + google-api-python-client."""
    mock_creds = MagicMock()
    mock_creds.valid = True

    google = ModuleType('google')
    google_auth = ModuleType('google.auth')
    google_oauth2 = ModuleType('google.oauth2')
    google_oauth2_creds = ModuleType('google.oauth2.credentials')
    google_oauth2_creds.Credentials = MagicMock(return_value=mock_creds)
    google_auth_transport = ModuleType('google.auth.transport')
    google_auth_transport_requests = ModuleType('google.auth.transport.requests')
    google_auth_transport_requests.Request = MagicMock()
    google_api = ModuleType('googleapiclient')
    google_api_discovery = ModuleType('googleapiclient.discovery')
    google_api_discovery.build = MagicMock()
    google_api_http = ModuleType('googleapiclient.http')
    google_api_http.MediaFileUpload = MagicMock()
    google_api_http.MediaIoBaseDownload = MagicMock()

    mocks = {
        'google': google,
        'google.auth': google_auth,
        'google.oauth2': google_oauth2,
        'google.oauth2.credentials': google_oauth2_creds,
        'google.auth.transport': google_auth_transport,
        'google.auth.transport.requests': google_auth_transport_requests,
        'googleapiclient': google_api,
        'googleapiclient.discovery': google_api_discovery,
        'googleapiclient.http': google_api_http,
    }
    return mocks, mock_creds


def _make_msal_mock():
    msal = ModuleType('msal')
    mock_msal_app = MagicMock()
    mock_msal_app.acquire_token_for_client.return_value = {
        'access_token': 'test_token_abc'
    }
    msal.ConfidentialClientApplication = MagicMock(return_value=mock_msal_app)
    return msal, mock_msal_app


# ─── GmailProvider ────────────────────────────────────────────────────────────

class TestGmailProvider:

    def _build(self, mock_creds):
        from flowforge.email_providers.gmail import GmailProvider
        mock_creds.refresh = MagicMock()
        return GmailProvider(
            client_id='cid',
            client_secret='csec',
            refresh_token='rtoken',
            sender='bot@example.com',
        )

    def test_init_refreshes_credentials(self):
        google_mocks, mock_creds = _make_google_mocks()
        with patch.dict(sys.modules, google_mocks):
            mock_creds.refresh = MagicMock()
            provider = self._build(mock_creds)
            mock_creds.refresh.assert_called_once()

    def test_send_success(self, tmp_path):
        google_mocks, mock_creds = _make_google_mocks()
        with patch.dict(sys.modules, google_mocks):
            mock_creds.refresh = MagicMock()
            provider = self._build(mock_creds)

            mock_service = MagicMock()
            google_mocks['googleapiclient.discovery'].build.return_value = mock_service
            mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {}

            result = provider.send(
                to=['a@b.com'],
                cc=[],
                bcc=[],
                subject='Hi',
                html_body='<p>Hello</p>',
                attachments=[],
            )
            assert result.success is True
            assert result.recipients == ['a@b.com']

    def test_send_with_attachment(self, tmp_path):
        google_mocks, mock_creds = _make_google_mocks()
        with patch.dict(sys.modules, google_mocks):
            mock_creds.refresh = MagicMock()
            provider = self._build(mock_creds)

            attachment = tmp_path / 'report.csv'
            attachment.write_bytes(b'col1,col2\n1,2\n')

            mock_service = MagicMock()
            google_mocks['googleapiclient.discovery'].build.return_value = mock_service
            mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {}

            result = provider.send(
                to=['a@b.com'],
                cc=['cc@b.com'],
                bcc=['bcc@b.com'],
                subject='Report',
                html_body='<p>See attachment</p>',
                attachments=[attachment],
            )
            assert result.success is True
            assert len(result.recipients) == 3

    def test_send_api_failure(self):
        google_mocks, mock_creds = _make_google_mocks()
        with patch.dict(sys.modules, google_mocks):
            mock_creds.refresh = MagicMock()
            provider = self._build(mock_creds)

            mock_service = MagicMock()
            google_mocks['googleapiclient.discovery'].build.return_value = mock_service
            mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = Exception('quota exceeded')

            result = provider.send(
                to=['a@b.com'], cc=[], bcc=[],
                subject='Hi', html_body='body', attachments=[],
            )
            assert result.success is False
            assert 'quota exceeded' in result.error

    def test_test_method_success(self):
        google_mocks, mock_creds = _make_google_mocks()
        with patch.dict(sys.modules, google_mocks):
            mock_creds.refresh = MagicMock()
            provider = self._build(mock_creds)
            ok, msg = provider.test()
            assert ok is True
            assert 'bot@example.com' in msg

    def test_test_method_failure(self):
        google_mocks, mock_creds = _make_google_mocks()
        with patch.dict(sys.modules, google_mocks):
            mock_creds.refresh = MagicMock()
            provider = self._build(mock_creds)
            mock_creds.refresh.side_effect = Exception('token revoked')
            ok, msg = provider.test()
            assert ok is False
            assert 'token revoked' in msg


# ─── Microsoft365Provider ─────────────────────────────────────────────────────

class TestMicrosoft365Provider:

    def _build(self, msal_mock):
        with patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider(
                tenant_id='tid',
                client_id='cid',
                client_secret='csec',
                sender_email='sender@corp.com',
            )
        return provider

    def test_init_builds_msal_app(self):
        msal_mock, msal_app = _make_msal_mock()
        with patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
        msal_mock.ConfidentialClientApplication.assert_called_once()

    def test_get_token_success(self):
        msal_mock, msal_app = _make_msal_mock()
        with patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
        token = provider._get_token()
        assert token == 'test_token_abc'

    def test_get_token_failure_raises(self):
        msal_mock, msal_app = _make_msal_mock()
        msal_app.acquire_token_for_client.return_value = {
            'error': 'invalid_client',
            'error_description': 'Bad secret',
        }
        with patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
        import pytest
        with pytest.raises(RuntimeError, match='Bad secret'):
            provider._get_token()

    def test_send_success(self, tmp_path):
        msal_mock, msal_app = _make_msal_mock()
        mock_requests = ModuleType('requests')
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_requests.post = MagicMock(return_value=mock_resp)

        with patch.dict(sys.modules, {'msal': msal_mock, 'requests': mock_requests}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
            result = provider.send(
                to=['a@b.com'],
                cc=[],
                bcc=[],
                subject='Test',
                html_body='<p>hi</p>',
                attachments=[],
            )
        assert result.success is True
        assert result.recipients == ['a@b.com']

    def test_send_with_attachment(self, tmp_path):
        msal_mock, msal_app = _make_msal_mock()
        mock_requests = ModuleType('requests')
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_requests.post = MagicMock(return_value=mock_resp)

        att = tmp_path / 'file.pdf'
        att.write_bytes(b'%PDF-1.4 content')

        with patch.dict(sys.modules, {'msal': msal_mock, 'requests': mock_requests}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
            result = provider.send(
                to=['a@b.com'], cc=['c@b.com'], bcc=[],
                subject='Report', html_body='body', attachments=[att],
            )

        assert result.success is True
        assert len(result.recipients) == 2

    def test_send_failure_returns_error_result(self):
        msal_mock, msal_app = _make_msal_mock()
        mock_requests = ModuleType('requests')
        mock_requests.post = MagicMock(side_effect=Exception('network error'))

        with patch.dict(sys.modules, {'msal': msal_mock, 'requests': mock_requests}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
            result = provider.send(
                to=['a@b.com'], cc=[], bcc=[],
                subject='Hi', html_body='body', attachments=[],
            )
        assert result.success is False
        assert 'network error' in result.error

    def test_test_method_success(self):
        msal_mock, msal_app = _make_msal_mock()
        with patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
        ok, msg = provider.test()
        assert ok is True
        assert 'sender@corp.com' in msg

    def test_test_method_failure(self):
        msal_mock, msal_app = _make_msal_mock()
        msal_app.acquire_token_for_client.return_value = {
            'error': 'invalid_client',
            'error_description': 'Bad',
        }
        with patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = Microsoft365Provider('tid', 'cid', 'csec', 'sender@corp.com')
        ok, msg = provider.test()
        assert ok is False


# ─── factory.get_email_provider ───────────────────────────────────────────────

class TestEmailProviderFactory:
    """
    factory.get_email_provider imports db and decrypt_config lazily inside the
    function body, so we patch at the source modules rather than the factory module.
    """

    def _make_row(self, provider_type: str):
        row = MagicMock()
        row.provider_type = provider_type
        row.config = {}
        return row

    def _db_patch(self, row):
        """Return a context manager that patches db.session.get to return row."""
        mock_db = MagicMock()
        mock_db.session.get.return_value = row
        return patch('flowforge.db.models.db', mock_db)

    def test_not_found_raises(self):
        mock_db = MagicMock()
        mock_db.session.get.return_value = None
        with patch('flowforge.db.models.db', mock_db):
            import pytest
            with pytest.raises(ValueError, match='not found'):
                from flowforge.email_providers.factory import get_email_provider
                get_email_provider('missing-id')

    def test_unsupported_type_raises(self):
        row = self._make_row('fax')
        with self._db_patch(row), \
             patch('flowforge.crypto.decrypt_config', return_value={'host': 'x'}):
            import pytest
            with pytest.raises(ValueError, match='Unsupported provider_type'):
                from flowforge.email_providers.factory import get_email_provider
                get_email_provider('some-id')

    def test_smtp_provider_returned(self):
        row = self._make_row('smtp')
        cfg = {'host': 'smtp.example.com', 'port': 587, 'username': 'u', 'password': 'p'}
        with self._db_patch(row), \
             patch('flowforge.crypto.decrypt_config', return_value=cfg):
            from flowforge.email_providers.factory import get_email_provider
            from flowforge.email_providers.smtp import SMTPProvider
            provider = get_email_provider('some-id')
            assert isinstance(provider, SMTPProvider)

    def test_gmail_provider_returned(self):
        row = self._make_row('gmail')
        cfg = {
            'client_id': 'cid', 'client_secret': 'csec',
            'refresh_token': 'rtoken', 'sender': 'bot@gmail.com',
        }
        google_mocks, mock_creds = _make_google_mocks()
        mock_creds.refresh = MagicMock()
        with self._db_patch(row), \
             patch('flowforge.crypto.decrypt_config', return_value=cfg), \
             patch.dict(sys.modules, google_mocks):
            from flowforge.email_providers.factory import get_email_provider
            from flowforge.email_providers.gmail import GmailProvider
            provider = get_email_provider('some-id')
            assert isinstance(provider, GmailProvider)

    def test_m365_provider_returned(self):
        row = self._make_row('microsoft365')
        cfg = {
            'tenant_id': 'tid', 'client_id': 'cid',
            'client_secret': 'csec', 'sender_email': 'x@corp.com',
        }
        msal_mock, _ = _make_msal_mock()
        with self._db_patch(row), \
             patch('flowforge.crypto.decrypt_config', return_value=cfg), \
             patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.factory import get_email_provider
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            provider = get_email_provider('some-id')
            assert isinstance(provider, Microsoft365Provider)

    def test_m365_missing_sender_raises(self):
        row = self._make_row('microsoft365')
        cfg = {'tenant_id': 'tid', 'client_id': 'cid', 'client_secret': 'csec'}
        msal_mock, _ = _make_msal_mock()
        with self._db_patch(row), \
             patch('flowforge.crypto.decrypt_config', return_value=cfg), \
             patch.dict(sys.modules, {'msal': msal_mock}):
            import pytest
            with pytest.raises(ValueError, match='sender'):
                from flowforge.email_providers.factory import get_email_provider
                get_email_provider('some-id')
