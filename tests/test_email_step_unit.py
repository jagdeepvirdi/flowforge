"""Unit tests for email_step._handle_attachments and _build_inline_provider.

No DB or real email providers are touched — all external I/O is mocked.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ─── _handle_attachments ─────────────────────────────────────────────────────

class TestHandleAttachments:

    def _call(self, attachments, max_mb=10, drive_folder='', drive_msg='',
              onedrive_folder='', context=None):
        from flowforge.steps.email_step import _handle_attachments
        return _handle_attachments(
            attachments, max_mb, drive_folder, drive_msg,
            context or {}, onedrive_folder_id=onedrive_folder,
        )

    def test_small_file_attached_directly(self, tmp_path):
        f = tmp_path / 'small.csv'
        f.write_bytes(b'x' * 100)
        direct, extra = self._call([f], max_mb=10)
        assert f in direct
        assert extra == ''

    def test_missing_file_skipped(self, tmp_path):
        f = tmp_path / 'ghost.xlsx'  # does not exist
        direct, extra = self._call([f])
        assert direct == []
        assert extra == ''

    def test_large_file_gdrive_upload(self, tmp_path):
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))  # 11 MB
        with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive/link') as mock_up:
            direct, extra = self._call([f], max_mb=10, drive_folder='folder-id')
        assert direct == []
        assert 'drive/link' in extra
        mock_up.assert_called_once_with(f, 'folder-id', make_shareable=True)

    def test_large_file_onedrive_upload_preferred(self, tmp_path):
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        with patch('flowforge.storage.onedrive.upload_file', return_value='https://onedrive/link') as mock_od, \
             patch('flowforge.storage.google_drive.upload_file') as mock_gd:
            direct, extra = self._call(
                [f], max_mb=10,
                drive_folder='gdrive-id',
                onedrive_folder='od-folder-id',
            )
        assert direct == []
        assert 'onedrive/link' in extra
        mock_od.assert_called_once()
        mock_gd.assert_not_called()

    def test_large_file_no_cloud_folder_attached_directly(self, tmp_path):
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        direct, extra = self._call([f], max_mb=10)
        assert f in direct
        assert extra == ''

    def test_drive_message_template_used(self, tmp_path):
        f = tmp_path / 'big.csv'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        custom_msg = 'Your file: {% for link in drive_links %}{{ link.filename }}{% endfor %}'
        with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive/x'):
            _, extra = self._call([f], max_mb=10, drive_folder='f1', drive_msg=custom_msg)
        assert 'big.csv' in extra

    def test_default_drive_message_used_when_no_template(self, tmp_path):
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive/y'):
            _, extra = self._call([f], max_mb=10, drive_folder='f2', drive_msg='')
        assert 'big.xlsx' in extra
        assert 'Google Drive' in extra

    def test_drive_upload_failure_falls_back_to_direct(self, tmp_path):
        """Drive upload failure must not fail the step — file attaches directly instead."""
        from flowforge.steps.email_step import _handle_attachments
        f = tmp_path / 'big.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        warnings: list[str] = []
        with patch('flowforge.storage.google_drive.upload_file', side_effect=Exception("API quota exceeded")):
            direct, extra = _handle_attachments(
                [f], 10, 'folder-id', '', {}, warnings_out=warnings,
            )
        assert f in direct          # fell back to direct attachment
        assert extra == ''          # no Drive link in body
        assert len(warnings) == 1
        assert 'Google Drive' in warnings[0]
        assert 'big.xlsx' in warnings[0]

    def test_onedrive_upload_failure_falls_back_to_direct(self, tmp_path):
        from flowforge.steps.email_step import _handle_attachments
        f = tmp_path / 'report.xlsx'
        f.write_bytes(b'x' * (11 * 1024 * 1024))
        warnings: list[str] = []
        with patch('flowforge.storage.onedrive.upload_file', side_effect=Exception("401 Unauthorized")):
            direct, extra = _handle_attachments(
                [f], 10, '', '', {}, onedrive_folder_id='od-folder', warnings_out=warnings,
            )
        assert f in direct
        assert len(warnings) == 1
        assert 'OneDrive' in warnings[0]

    def test_multiple_attachments_mixed(self, tmp_path):
        small = tmp_path / 'small.csv'
        small.write_bytes(b'x' * 100)
        large = tmp_path / 'large.xlsx'
        large.write_bytes(b'x' * (11 * 1024 * 1024))
        with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive/z'):
            direct, extra = self._call([small, large], max_mb=10, drive_folder='fid')
        assert small in direct
        assert large not in direct
        assert extra != ''


# ─── _build_inline_provider ──────────────────────────────────────────────────

class TestBuildInlineProvider:

    def test_smtp_is_default(self):
        from flowforge.email_providers.smtp import SMTPProvider
        from flowforge.steps.email_step import _build_inline_provider
        p = _build_inline_provider({'host': 'smtp.test.com', 'port': 587})
        assert isinstance(p, SMTPProvider)

    def test_smtp_explicit(self):
        from flowforge.email_providers.smtp import SMTPProvider
        from flowforge.steps.email_step import _build_inline_provider
        p = _build_inline_provider({'provider_type': 'smtp', 'host': 'smtp.x.com'})
        assert isinstance(p, SMTPProvider)

    def test_gmail_inline(self, monkeypatch):
        monkeypatch.setenv('GMAIL_CLIENT_ID', 'cid')
        monkeypatch.setenv('GMAIL_CLIENT_SECRET', 'csec')
        monkeypatch.setenv('GMAIL_REFRESH_TOKEN', 'rtoken')
        monkeypatch.setenv('GMAIL_SENDER', 'bot@gmail.com')

        google_mocks = _make_google_mocks()
        with patch.dict(sys.modules, google_mocks):
            from flowforge.email_providers.gmail import GmailProvider
            from flowforge.steps.email_step import _build_inline_provider
            p = _build_inline_provider({'provider_type': 'gmail'})
            assert isinstance(p, GmailProvider)

    def test_m365_inline(self, monkeypatch):
        monkeypatch.setenv('MICROSOFT_TENANT_ID', 'tid')
        monkeypatch.setenv('MICROSOFT_CLIENT_ID', 'cid')
        monkeypatch.setenv('MICROSOFT_CLIENT_SECRET', 'csec')
        monkeypatch.setenv('MICROSOFT_SENDER_EMAIL', 'x@corp.com')

        msal_mock = ModuleType('msal')
        msal_app = MagicMock()
        msal_mock.ConfidentialClientApplication = MagicMock(return_value=msal_app)
        with patch.dict(sys.modules, {'msal': msal_mock}):
            from flowforge.email_providers.microsoft365 import Microsoft365Provider
            from flowforge.steps.email_step import _build_inline_provider
            p = _build_inline_provider({'provider_type': 'microsoft365'})
            assert isinstance(p, Microsoft365Provider)


# ─── EmailStep.run via inline config ─────────────────────────────────────────

class TestEmailStepRun:

    def _make_step(self, config: dict):
        from flowforge.steps.email_step import EmailStep
        step = EmailStep.__new__(EmailStep)
        step.config = config
        step.name = 'email_step'
        return step

    def test_run_success_with_inline_smtp(self, tmp_path):
        attachment = tmp_path / 'report.csv'
        attachment.write_bytes(b'a,b,c')
        mock_provider = MagicMock()
        mock_provider.send.return_value = MagicMock(success=True, recipients=['a@b.com'])

        step = self._make_step({
            'inline_config': {
                'provider_type': 'smtp',
                'subject': 'Test',
                'body_template': 'Hello',
                'to_addresses': ['a@b.com'],
            },
            'attachments': [str(attachment)],
        })

        with patch('flowforge.steps.email_step._build_inline_provider', return_value=mock_provider), \
             patch('flowforge.audit.log_email_sent'):
            result = step.run({'steps': {}})

        assert result.success is True
        mock_provider.send.assert_called_once()

    def test_run_passes_run_id_from_context_to_audit_log(self):
        """7.4: EMAIL_SENT/REPORT_EXPORTED audit rows must carry run_id so they
        can be joined directly to pipeline_runs/step_runs."""
        mock_provider = MagicMock()
        mock_provider.send.return_value = MagicMock(success=True, recipients=['a@b.com'])

        step = self._make_step({
            'inline_config': {
                'provider_type': 'smtp',
                'subject': 'Test',
                'body_template': 'Hello',
                'to_addresses': ['a@b.com'],
            },
            'attachments': [],
        })

        with patch('flowforge.steps.email_step._build_inline_provider', return_value=mock_provider), \
             patch('flowforge.audit.log_email_sent') as mock_log:
            result = step.run({'steps': {}, 'run_id': 'run-999'})

        assert result.success is True
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs['run_id'] == 'run-999'

    def test_run_failure_provider_returns_error(self):
        mock_provider = MagicMock()
        mock_provider.send.return_value = MagicMock(success=False, error='auth failed')

        step = self._make_step({
            'inline_config': {
                'provider_type': 'smtp',
                'subject': 'Hi',
                'body_template': 'body',
                'to_addresses': ['x@y.com'],
            },
        })

        with patch('flowforge.steps.email_step._build_inline_provider', return_value=mock_provider):
            result = step.run({'steps': {}})

        assert result.success is False
        assert 'auth failed' in result.error

    def test_run_exception_caught(self):
        mock_provider = MagicMock()
        mock_provider.send.side_effect = RuntimeError('network down')

        step = self._make_step({
            'inline_config': {
                'provider_type': 'smtp',
                'subject': 'Hi',
                'body_template': 'body',
                'to_addresses': ['x@y.com'],
            },
        })

        with patch('flowforge.steps.email_step._build_inline_provider', return_value=mock_provider):
            result = step.run({'steps': {}})

        assert result.success is False
        assert 'network down' in result.error

    def test_resolve_recipients_falls_back_to_to_addresses(self):
        from flowforge.steps.email_step import EmailStep
        step = EmailStep.__new__(EmailStep)
        step.config = {}
        step.name = 'e'
        cfg = {'to_addresses': ['direct@x.com']}
        recipients = step._resolve_recipients(cfg)
        assert recipients == ['direct@x.com']

    def test_resolve_recipients_uses_group(self):
        from flowforge.steps.email_step import EmailStep
        step = EmailStep.__new__(EmailStep)
        step.config = {}
        step.name = 'e'

        mock_group = MagicMock()
        mock_group.addresses = ['a@team.com', 'b@team.com']
        mock_db = MagicMock()
        mock_db.session.get.return_value = mock_group

        with patch('flowforge.db.models.db', mock_db):
            recipients = step._resolve_recipients({'recipient_group_id': 'group-uuid'})

        assert recipients == ['a@team.com', 'b@team.com']

    def test_resolve_recipients_group_not_found_falls_back(self):
        from flowforge.steps.email_step import EmailStep
        step = EmailStep.__new__(EmailStep)
        step.config = {}
        step.name = 'e'

        mock_db = MagicMock()
        mock_db.session.get.return_value = None

        with patch('flowforge.db.models.db', mock_db):
            recipients = step._resolve_recipients({
                'recipient_group_id': 'missing',
                'to_addresses': ['fallback@x.com'],
            })

        assert recipients == ['fallback@x.com']


class TestEmailStepLoadConfig:
    """Tests for _load_config_and_provider using email_config_id DB path."""

    def _make_step(self, config: dict):
        from flowforge.steps.email_step import EmailStep
        step = EmailStep.__new__(EmailStep)
        step.config = config
        step.name = 'email_step'
        return step

    def _make_email_row(self, **kwargs):
        row = MagicMock()
        row.subject = kwargs.get('subject', 'Hi')
        row.body_template = kwargs.get('body_template', '<p>body</p>')
        row.to_addresses = kwargs.get('to_addresses', ['a@b.com'])
        row.cc_addresses = kwargs.get('cc_addresses', [])
        row.bcc_addresses = kwargs.get('bcc_addresses', [])
        row.recipient_group_id = kwargs.get('recipient_group_id', None)
        row.attachment_max_mb = kwargs.get('attachment_max_mb', 10)
        row.drive_folder_id = kwargs.get('drive_folder_id', None)
        row.drive_share_message = kwargs.get('drive_share_message', None)
        row.onedrive_folder_id = kwargs.get('onedrive_folder_id', None)
        row.provider_id = kwargs.get('provider_id', 'provider-uuid')
        return row

    def test_load_config_from_db_returns_cfg_and_provider(self):
        row = self._make_email_row()
        mock_db = MagicMock()
        mock_db.session.get.return_value = row
        mock_provider = MagicMock()

        step = self._make_step({'email_config_id': 'cfg-uuid'})

        with patch('flowforge.db.models.db', mock_db), \
             patch('flowforge.email_providers.factory.get_email_provider', return_value=mock_provider):
            cfg, provider = step._load_config_and_provider()

        assert cfg['subject'] == 'Hi'
        assert provider is mock_provider

    def test_load_config_raises_when_not_found(self):
        mock_db = MagicMock()
        mock_db.session.get.return_value = None
        step = self._make_step({'email_config_id': 'missing-uuid'})

        with patch('flowforge.db.models.db', mock_db):
            with pytest.raises(ValueError, match='not found'):
                step._load_config_and_provider()

    def test_load_config_raises_when_no_provider(self):
        row = self._make_email_row(provider_id=None)
        mock_db = MagicMock()
        mock_db.session.get.return_value = row
        step = self._make_step({'email_config_id': 'cfg-uuid'})

        with patch('flowforge.db.models.db', mock_db):
            with pytest.raises(ValueError, match='no provider'):
                step._load_config_and_provider()

    def test_load_config_maps_all_fields(self):
        row = self._make_email_row(
            subject='Monthly Report',
            cc_addresses=['cc@x.com'],
            drive_folder_id='gdrive-f',
            onedrive_folder_id='od-f',
        )
        mock_db = MagicMock()
        mock_db.session.get.return_value = row
        mock_provider = MagicMock()
        step = self._make_step({'email_config_id': 'cfg-uuid'})

        with patch('flowforge.db.models.db', mock_db), \
             patch('flowforge.email_providers.factory.get_email_provider', return_value=mock_provider):
            cfg, _ = step._load_config_and_provider()

        assert cfg['subject'] == 'Monthly Report'
        assert cfg['cc_addresses'] == ['cc@x.com']
        assert cfg['drive_folder_id'] == 'gdrive-f'
        assert cfg['onedrive_folder_id'] == 'od-f'


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_google_mocks():
    mock_creds = MagicMock()
    mock_creds.refresh = MagicMock()
    google_oauth2_creds = ModuleType('google.oauth2.credentials')
    google_oauth2_creds.Credentials = MagicMock(return_value=mock_creds)
    google_auth_transport_requests = ModuleType('google.auth.transport.requests')
    google_auth_transport_requests.Request = MagicMock()
    return {
        'google': ModuleType('google'),
        'google.auth': ModuleType('google.auth'),
        'google.oauth2': ModuleType('google.oauth2'),
        'google.oauth2.credentials': google_oauth2_creds,
        'google.auth.transport': ModuleType('google.auth.transport'),
        'google.auth.transport.requests': google_auth_transport_requests,
        'googleapiclient': ModuleType('googleapiclient'),
        'googleapiclient.discovery': ModuleType('googleapiclient.discovery'),
        'googleapiclient.http': ModuleType('googleapiclient.http'),
    }
