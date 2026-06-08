"""Tests for email_step.py branches not covered by test_email_step_unit.py:
onedrive upload failure, gdrive upload failure with warnings_out,
send_only_on_failure suppression, _build_inline_provider branches.
"""
from unittest.mock import MagicMock, patch


class TestHandleAttachmentsCoverage:

    def _call(self, attachments, max_mb=10, drive_folder='', drive_msg='',
              onedrive_folder='', context=None, warnings_out=None):
        from flowforge.steps.email_step import _handle_attachments
        return _handle_attachments(
            attachments, max_mb, drive_folder, drive_msg,
            context or {}, onedrive_folder_id=onedrive_folder,
            warnings_out=warnings_out,
        )

    def test_onedrive_upload_success(self, tmp_path):
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        mock_upload = MagicMock(return_value='https://onedrive/link')
        with patch('flowforge.storage.onedrive.upload_file', mock_upload):
            direct, extra = self._call([f], max_mb=10, onedrive_folder='folder-id')
        assert direct == []
        assert 'onedrive/link' in extra

    def test_onedrive_upload_failure_falls_back_to_direct(self, tmp_path):
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        warnings: list[str] = []
        with patch('flowforge.storage.onedrive.upload_file',
                   side_effect=Exception('upload failed')):
            direct, extra = self._call([f], max_mb=10, onedrive_folder='folder-id',
                                       warnings_out=warnings)
        assert f in direct
        assert extra == ''
        assert len(warnings) == 1
        assert 'onedrive' in warnings[0].lower()

    def test_gdrive_upload_failure_falls_back_to_direct(self, tmp_path):
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        warnings: list[str] = []
        with patch('flowforge.storage.google_drive.upload_file',
                   side_effect=Exception('gdrive down')):
            direct, extra = self._call([f], max_mb=10, drive_folder='gd-folder',
                                       warnings_out=warnings)
        assert f in direct
        assert extra == ''
        assert len(warnings) == 1
        assert 'google drive' in warnings[0].lower()

    def test_no_cloud_folder_large_file_attached_directly(self, tmp_path):
        """Large file with no drive or onedrive folder → attached directly."""
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        direct, extra = self._call([f], max_mb=10, drive_folder='', onedrive_folder='')
        assert f in direct
        assert extra == ''

    def test_missing_file_skipped_with_no_warning(self, tmp_path):
        missing = tmp_path / 'ghost.xlsx'
        direct, extra = self._call([missing])
        assert direct == []
        assert extra == ''


# ── EmailStep.run — send_only_on_failure suppression ─────────────────────────

def test_email_step_suppressed_when_send_only_on_failure(tmp_path):
    from flowforge.steps.email_step import EmailStep
    step = EmailStep(name='notify', config={})
    context = {
        'pipeline_send_only_on_failure': 'true',
        '_pipeline_has_failed': False,
        'steps': {},
    }
    result = step.run(context)
    assert result.success
    assert 'suppressed' in (result.logs or '').lower()


def test_email_step_not_suppressed_when_pipeline_failed(tmp_path):
    """When send_only_on_failure=true AND pipeline failed, email should proceed (not suppress)."""
    from flowforge.steps.email_step import EmailStep
    step = EmailStep(name='notify', config={'email_config_id': None, 'inline_config': {}})
    context = {
        'pipeline_send_only_on_failure': 'true',
        '_pipeline_has_failed': True,
        'steps': {},
    }
    # The step will try to load a provider and fail — that's OK, we just verify
    # it didn't return the suppressed result
    result = step.run(context)
    assert result.logs != 'Email suppressed (routine email suppression)'


# ── _build_inline_provider branches ──────────────────────────────────────────

def test_build_inline_provider_gmail():
    from flowforge.steps.email_step import _build_inline_provider
    mock_creds = MagicMock()
    mock_creds_cls = MagicMock(return_value=mock_creds)
    mock_request = MagicMock()
    import sys
    fake_google_oauth2_creds = MagicMock()
    fake_google_oauth2_creds.Credentials = mock_creds_cls
    fake_google_auth_transport_requests = MagicMock()
    fake_google_auth_transport_requests.Request = mock_request
    with patch.dict('os.environ', {
        'GMAIL_CLIENT_ID': 'cid',
        'GMAIL_CLIENT_SECRET': 'csecret',
        'GMAIL_REFRESH_TOKEN': 'rtoken',
        'GMAIL_SENDER': 'sender@gmail.com',
    }), patch.dict(sys.modules, {
        'google.oauth2.credentials': fake_google_oauth2_creds,
        'google.auth.transport.requests': fake_google_auth_transport_requests,
    }):
        provider = _build_inline_provider({'provider_type': 'gmail'})
    assert type(provider).__name__ == 'GmailProvider'


def test_build_inline_provider_microsoft365():
    from flowforge.steps.email_step import _build_inline_provider
    mock_app = MagicMock()
    mock_msal = MagicMock()
    mock_msal.ConfidentialClientApplication.return_value = mock_app
    import sys
    with patch.dict('os.environ', {
        'MICROSOFT_TENANT_ID': 'tid',
        'MICROSOFT_CLIENT_ID': 'cid',
        'MICROSOFT_CLIENT_SECRET': 'csecret',
        'MICROSOFT_SENDER_EMAIL': 'sender@company.com',
    }), patch.dict(sys.modules, {'msal': mock_msal}):
        provider = _build_inline_provider({'provider_type': 'microsoft365'})
    assert type(provider).__name__ == 'Microsoft365Provider'


def test_build_inline_provider_smtp_default():
    from flowforge.steps.email_step import _build_inline_provider
    provider = _build_inline_provider({
        'provider_type': 'smtp',
        'host': 'smtp.example.com',
        'port': 587,
        'username': 'u',
        'password': 'p',
    })
    from flowforge.email_providers.smtp import SMTPProvider
    assert isinstance(provider, SMTPProvider)
