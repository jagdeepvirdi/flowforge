"""Tests for steps/drive_upload.py and storage/google_drive.py."""
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch, call

import pytest


def _make_google_mocks():
    """Minimal mock set for googleapiclient + google-auth."""
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.refresh = MagicMock()

    google_auth_transport = ModuleType('google.auth.transport')
    google_auth_transport_requests = ModuleType('google.auth.transport.requests')
    google_auth_transport_requests.Request = MagicMock()

    google_oauth2 = ModuleType('google.oauth2')
    google_oauth2_creds = ModuleType('google.oauth2.credentials')
    google_oauth2_creds.Credentials = MagicMock(return_value=mock_creds)
    google_oauth2_service = ModuleType('google.oauth2.service_account')
    google_oauth2_service.Credentials = MagicMock(return_value=mock_creds)

    google = ModuleType('google')
    google_auth = ModuleType('google.auth')

    mock_service = MagicMock()
    google_api = ModuleType('googleapiclient')
    google_api_discovery = ModuleType('googleapiclient.discovery')
    google_api_discovery.build = MagicMock(return_value=mock_service)
    google_api_http = ModuleType('googleapiclient.http')
    google_api_http.MediaFileUpload = MagicMock()
    google_api_http.MediaIoBaseDownload = MagicMock()

    mocks = {
        'google': google,
        'google.auth': google_auth,
        'google.oauth2': google_oauth2,
        'google.oauth2.credentials': google_oauth2_creds,
        'google.oauth2.service_account': google_oauth2_service,
        'google.auth.transport': google_auth_transport,
        'google.auth.transport.requests': google_auth_transport_requests,
        'googleapiclient': google_api,
        'googleapiclient.discovery': google_api_discovery,
        'googleapiclient.http': google_api_http,
    }
    return mocks, mock_service, mock_creds


# ─── DriveUploadStep ─────────────────────────────────────────────────────────

class TestDriveUploadStep:

    def _make_step(self, config: dict):
        from flowforge.steps.drive_upload import DriveUploadStep
        step = DriveUploadStep.__new__(DriveUploadStep)
        step.config = config
        step.name = 'drive_upload_step'
        return step

    def test_successful_upload(self, tmp_path):
        file = tmp_path / 'report.xlsx'
        file.write_bytes(b'data')
        step = self._make_step({'file_path': str(file), 'folder_id': 'folder123'})

        with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/file/d/abc/view') as mock_upload:
            result = step.run({'steps': {}})

        assert result.success is True
        assert result.drive_url.startswith('https://drive.google.com/')
        mock_upload.assert_called_once_with(file, 'folder123', make_shareable=True)

    def test_upload_failure_returns_error(self, tmp_path):
        file = tmp_path / 'report.xlsx'
        file.write_bytes(b'data')
        step = self._make_step({'file_path': str(file), 'folder_id': ''})

        with patch('flowforge.storage.google_drive.upload_file', side_effect=Exception('quota exceeded')):
            result = step.run({'steps': {}})

        assert result.success is False
        assert 'quota exceeded' in result.error

    def test_rename_to_renames_file(self, tmp_path):
        original = tmp_path / 'report_raw.xlsx'
        original.write_bytes(b'content')
        step = self._make_step({
            'file_path': str(original),
            'folder_id': 'f1',
            'rename_to': 'report_final.xlsx',
        })

        captured_path = {}

        def capture_upload(path, folder_id, make_shareable=False):
            captured_path['path'] = path
            return 'https://drive.google.com/file/d/xyz/view'

        with patch('flowforge.storage.google_drive.upload_file', side_effect=capture_upload):
            result = step.run({'steps': {}})

        assert result.success is True
        assert captured_path['path'].name == 'report_final.xlsx'

    def test_empty_folder_id(self, tmp_path):
        file = tmp_path / 'rep.csv'
        file.write_bytes(b'a,b')
        step = self._make_step({'file_path': str(file), 'folder_id': ''})

        with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/file/d/no-folder/view') as mock_upload:
            result = step.run({'steps': {}})

        assert result.success is True
        mock_upload.assert_called_once_with(file, '', make_shareable=True)

    def test_context_variables_rendered(self, tmp_path):
        file = tmp_path / 'report.csv'
        file.write_bytes(b'x')
        step = self._make_step({
            'file_path': str(file),
            'folder_id': '{{ env.DRIVE_FOLDER }}',
        })
        ctx = {'env': {'DRIVE_FOLDER': 'folder-from-env'}, 'steps': {}}

        with patch('flowforge.storage.google_drive.upload_file', return_value='https://example.com') as mock_upload:
            result = step.run(ctx)

        assert result.success is True
        mock_upload.assert_called_once_with(file, 'folder-from-env', make_shareable=True)


# ─── storage/google_drive.py ─────────────────────────────────────────────────

class TestGoogleDriveStorage:

    def test_upload_file_no_folder(self, tmp_path):
        """upload_file with empty folder_id passes empty parents list."""
        file = tmp_path / 'test.csv'
        file.write_bytes(b'a,b,c')

        google_mocks, mock_service, _ = _make_google_mocks()
        mock_service.files.return_value.create.return_value.execute.return_value = {'id': 'file1'}
        mock_service.permissions.return_value.create.return_value.execute.return_value = {}

        with patch.dict(sys.modules, google_mocks):
            from flowforge.storage.google_drive import upload_file
            result = upload_file(file, folder_id='', make_shareable=False)

        assert result == 'file1'

    def test_upload_file_with_folder_and_shareable(self, tmp_path):
        file = tmp_path / 'report.xlsx'
        file.write_bytes(b'xlsx_data')

        google_mocks, mock_service, _ = _make_google_mocks()
        mock_service.files.return_value.create.return_value.execute.return_value = {'id': 'file2'}
        mock_service.permissions.return_value.create.return_value.execute.return_value = {}

        with patch.dict(sys.modules, google_mocks):
            from flowforge.storage.google_drive import upload_file
            url = upload_file(file, folder_id='folder-abc', make_shareable=True)

        assert 'file2' in url
        assert 'drive.google.com' in url

    def test_create_folder_returns_id(self):
        google_mocks, mock_service, _ = _make_google_mocks()
        mock_service.files.return_value.create.return_value.execute.return_value = {'id': 'new-folder'}

        with patch.dict(sys.modules, google_mocks):
            from flowforge.storage.google_drive import create_folder
            folder_id = create_folder('Reports 2026', parent_id='parent-folder')

        assert folder_id == 'new-folder'

    def test_create_folder_no_parent(self):
        google_mocks, mock_service, _ = _make_google_mocks()
        mock_service.files.return_value.create.return_value.execute.return_value = {'id': 'root-folder'}

        with patch.dict(sys.modules, google_mocks):
            from flowforge.storage.google_drive import create_folder
            folder_id = create_folder('Root Folder')

        assert folder_id == 'root-folder'

    def test_download_file(self, tmp_path):
        dest = tmp_path / 'downloaded.xlsx'
        google_mocks, mock_service, _ = _make_google_mocks()

        # MediaIoBaseDownload mock
        mock_downloader = MagicMock()
        mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
        google_mocks['googleapiclient.http'].MediaIoBaseDownload.return_value = mock_downloader

        with patch.dict(sys.modules, google_mocks), \
             patch('io.FileIO', MagicMock(return_value=MagicMock().__enter__.return_value)):
            from flowforge.storage.google_drive import download_file
            download_file('file-xyz', dest)

        mock_service.files.return_value.get_media.assert_called_once_with(fileId='file-xyz')

    def test_get_service_uses_service_account(self, tmp_path, monkeypatch):
        """When GOOGLE_SERVICE_ACCOUNT_FILE is set, service account creds are used."""
        sa_file = tmp_path / 'sa.json'
        sa_file.write_text('{}')
        monkeypatch.setenv('GOOGLE_SERVICE_ACCOUNT_FILE', str(sa_file))

        google_mocks, mock_service, mock_creds = _make_google_mocks()
        sa_creds = MagicMock()
        google_mocks['google.oauth2.service_account'].Credentials.from_service_account_file = MagicMock(return_value=sa_creds)

        with patch.dict(sys.modules, google_mocks):
            # Force re-import to pick up fresh env
            if 'flowforge.storage.google_drive' in sys.modules:
                del sys.modules['flowforge.storage.google_drive']
            from flowforge.storage.google_drive import _get_service
            _get_service()

        google_mocks['google.oauth2.service_account'].Credentials.from_service_account_file.assert_called_once_with(
            str(sa_file), scopes=['https://www.googleapis.com/auth/drive']
        )
