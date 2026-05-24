"""Tests for OneDrive storage module and OneDriveUploadStep."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


# ── storage: onedrive.upload_file ─────────────────────────────────────────────

@pytest.fixture
def tmp_small_file(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_bytes(b'x' * 100)
    return f


@pytest.fixture
def tmp_large_file(tmp_path):
    # Larger than 4 MB chunk threshold
    f = tmp_path / 'big_report.xlsx'
    f.write_bytes(b'y' * (5 * 1024 * 1024))
    return f


def _mock_msal_token():
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {'access_token': 'test-token'}
    return mock_app


@patch.dict(os.environ, {
    'MICROSOFT_TENANT_ID': 'tenant1',
    'MICROSOFT_CLIENT_ID': 'client1',
    'MICROSOFT_CLIENT_SECRET': 'secret1',
    'MICROSOFT_SENDER_EMAIL': 'sender@example.com',
})
@patch('flowforge.storage.onedrive.msal', create=True)
def test_upload_small_file_direct(mock_msal_mod, tmp_small_file):
    """Small files use a direct PUT and return item ID."""
    import msal as _msal
    mock_msal_mod.ConfidentialClientApplication.return_value = _mock_msal_token()

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {'id': 'item-abc'}

    mock_requests = MagicMock()
    mock_requests.put.return_value = mock_resp

    with patch.dict('sys.modules', {'msal': mock_msal_mod, 'requests': mock_requests}):
        from importlib import reload
        import flowforge.storage.onedrive as mod
        reload(mod)
        result = mod.upload_file(tmp_small_file, 'root')

    assert result == 'item-abc'
    mock_requests.put.assert_called_once()


@patch.dict(os.environ, {
    'MICROSOFT_TENANT_ID': 'tenant1',
    'MICROSOFT_CLIENT_ID': 'client1',
    'MICROSOFT_CLIENT_SECRET': 'secret1',
    'MICROSOFT_SENDER_EMAIL': 'sender@example.com',
})
@patch('flowforge.storage.onedrive.msal', create=True)
def test_upload_returns_share_url(mock_msal_mod, tmp_small_file):
    """make_shareable=True posts createLink and returns the webUrl."""
    mock_msal_mod.ConfidentialClientApplication.return_value = _mock_msal_token()

    upload_resp = MagicMock()
    upload_resp.status_code = 201
    upload_resp.json.return_value = {'id': 'item-xyz'}

    link_resp = MagicMock()
    link_resp.json.return_value = {'link': {'webUrl': 'https://1drv.ms/b/s!xyz'}}

    mock_requests = MagicMock()
    mock_requests.put.return_value = upload_resp
    mock_requests.post.return_value = link_resp

    with patch.dict('sys.modules', {'msal': mock_msal_mod, 'requests': mock_requests}):
        from importlib import reload
        import flowforge.storage.onedrive as mod
        reload(mod)
        url = mod.upload_file(tmp_small_file, 'root', make_shareable=True)

    assert url == 'https://1drv.ms/b/s!xyz'
    mock_requests.post.assert_called_once()
    post_args = mock_requests.post.call_args
    assert post_args[1]['json'] == {'type': 'view', 'scope': 'anonymous'}


@patch.dict(os.environ, {
    'MICROSOFT_TENANT_ID': 'tenant1',
    'MICROSOFT_CLIENT_ID': 'client1',
    'MICROSOFT_CLIENT_SECRET': 'secret1',
    'MICROSOFT_SENDER_EMAIL': '',
})
@patch('flowforge.storage.onedrive.msal', create=True)
def test_upload_requires_user_email(mock_msal_mod, tmp_small_file):
    """Raises ValueError when no user email is available."""
    mock_msal_mod.ConfidentialClientApplication.return_value = _mock_msal_token()

    mock_requests = MagicMock()
    with patch.dict('sys.modules', {'msal': mock_msal_mod, 'requests': mock_requests}):
        from importlib import reload
        import flowforge.storage.onedrive as mod
        reload(mod)
        with pytest.raises(ValueError, match='MICROSOFT_SENDER_EMAIL'):
            mod.upload_file(tmp_small_file, 'root')


@patch.dict(os.environ, {
    'MICROSOFT_TENANT_ID': 'tenant1',
    'MICROSOFT_CLIENT_ID': 'client1',
    'MICROSOFT_CLIENT_SECRET': 'secret1',
    'MICROSOFT_SENDER_EMAIL': 'sender@example.com',
})
@patch('flowforge.storage.onedrive.msal', create=True)
def test_upload_uses_folder_id_in_path(mock_msal_mod, tmp_small_file):
    """A non-root folder_id is embedded in the PUT URL."""
    mock_msal_mod.ConfidentialClientApplication.return_value = _mock_msal_token()

    upload_resp = MagicMock()
    upload_resp.status_code = 201
    upload_resp.json.return_value = {'id': 'item-123'}

    mock_requests = MagicMock()
    mock_requests.put.return_value = upload_resp

    with patch.dict('sys.modules', {'msal': mock_msal_mod, 'requests': mock_requests}):
        from importlib import reload
        import flowforge.storage.onedrive as mod
        reload(mod)
        mod.upload_file(tmp_small_file, 'FOLDERID123')

    put_url = mock_requests.put.call_args[0][0]
    assert 'FOLDERID123' in put_url


# ── step: OneDriveUploadStep ───────────────────────────────────────────────────

def test_onedrive_upload_step_success(tmp_path):
    """Step returns success=True and populates drive_url."""
    f = tmp_path / 'out.xlsx'
    f.write_bytes(b'data')

    from flowforge.steps.onedrive_upload import OneDriveUploadStep

    step = OneDriveUploadStep(
        name='upload_report',
        config={'file_path': str(f), 'folder_id': 'root'},
    )

    with patch('flowforge.storage.onedrive.upload_file', return_value='https://1drv.ms/xyz') as mock_up:
        result = step.run({'steps': {}})

    assert result.success
    assert result.drive_url == 'https://1drv.ms/xyz'
    mock_up.assert_called_once_with(f, 'root', make_shareable=True, user_email='')


def test_onedrive_upload_step_rename(tmp_path):
    """rename_to renames the file before upload."""
    f = tmp_path / 'report_raw.xlsx'
    f.write_bytes(b'data')

    from flowforge.steps.onedrive_upload import OneDriveUploadStep

    step = OneDriveUploadStep(
        name='upload_renamed',
        config={
            'file_path': str(f),
            'folder_id': 'root',
            'rename_to': 'report_final.xlsx',
        },
    )

    with patch('flowforge.storage.onedrive.upload_file', return_value='https://1drv.ms/abc') as mock_up:
        result = step.run({'steps': {}})

    assert result.success
    uploaded_path = mock_up.call_args[0][0]
    assert uploaded_path.name == 'report_final.xlsx'


def test_onedrive_upload_step_failure(tmp_path):
    """Upload errors are caught and returned as failed StepResult."""
    f = tmp_path / 'out.xlsx'
    f.write_bytes(b'data')

    from flowforge.steps.onedrive_upload import OneDriveUploadStep

    step = OneDriveUploadStep(
        name='upload_fail',
        config={'file_path': str(f), 'folder_id': 'root'},
    )

    with patch('flowforge.storage.onedrive.upload_file', side_effect=RuntimeError('auth failed')):
        result = step.run({'steps': {}})

    assert not result.success
    assert 'auth failed' in result.error


# ── email smart-attachment routing ────────────────────────────────────────────

def test_handle_attachments_routes_to_onedrive_when_folder_set(tmp_path):
    """Large attachments go to OneDrive when onedrive_folder_id is configured."""
    big = tmp_path / 'big.xlsx'
    big.write_bytes(b'z' * (15 * 1024 * 1024))  # 15 MB

    from flowforge.steps.email_step import _handle_attachments

    with patch('flowforge.storage.onedrive.upload_file', return_value='https://1drv.ms/big') as mock_od, \
         patch('flowforge.storage.google_drive.upload_file') as mock_gd:
        direct, extra = _handle_attachments(
            [big], max_mb=10, drive_folder_id='',
            drive_message_template='', context={},
            onedrive_folder_id='OD_FOLDER_ID',
        )

    assert direct == []
    mock_od.assert_called_once()
    mock_gd.assert_not_called()
    assert 'https://1drv.ms/big' in extra


def test_handle_attachments_falls_back_to_gdrive(tmp_path):
    """Falls back to Google Drive when onedrive_folder_id is not set."""
    big = tmp_path / 'big.xlsx'
    big.write_bytes(b'z' * (15 * 1024 * 1024))

    from flowforge.steps.email_step import _handle_attachments

    with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/file/xyz') as mock_gd:
        direct, extra = _handle_attachments(
            [big], max_mb=10, drive_folder_id='GD_FOLDER',
            drive_message_template='', context={},
            onedrive_folder_id='',
        )

    assert direct == []
    mock_gd.assert_called_once()
    assert 'https://drive.google.com/file/xyz' in extra


def test_handle_attachments_attaches_directly_when_no_cloud(tmp_path):
    """Large file is attached directly when neither cloud folder is configured."""
    big = tmp_path / 'big.xlsx'
    big.write_bytes(b'z' * (15 * 1024 * 1024))

    from flowforge.steps.email_step import _handle_attachments

    direct, extra = _handle_attachments(
        [big], max_mb=10, drive_folder_id='',
        drive_message_template='', context={},
        onedrive_folder_id='',
    )

    assert big in direct
    assert extra == ''
