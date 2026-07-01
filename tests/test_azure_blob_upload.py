"""Tests for flowforge/storage/azure_blob.py and flowforge/steps/azure_blob_upload.py."""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

# ── storage layer — flowforge/storage/azure_blob.py ─────────────────────────────

def _make_azure_mock():
    blob_client = MagicMock()
    blob_client.url = 'https://myaccount.blob.core.windows.net/mycontainer/report.xlsx'
    blob_client.account_name = 'myaccount'

    container_client = MagicMock()
    container_client.upload_blob.return_value = blob_client

    service_client = MagicMock()
    service_client.get_container_client.return_value = container_client

    blob_mod = ModuleType('azure.storage.blob')
    blob_mod.BlobServiceClient = MagicMock()
    blob_mod.BlobServiceClient.from_connection_string = MagicMock(return_value=service_client)
    blob_mod.BlobServiceClient.side_effect = lambda **kw: service_client
    blob_mod.BlobSasPermissions = MagicMock(return_value='read-perm')
    blob_mod.generate_blob_sas = MagicMock(return_value='sv=2021&sig=abc')

    return blob_mod, service_client, container_client, blob_client


def test_upload_file_import_error_when_sdk_missing(tmp_path, monkeypatch):
    monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', 'fake')
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    with patch.dict(sys.modules, {'azure.storage.blob': None}):
        from flowforge.storage.azure_blob import upload_file
        try:
            upload_file(f, 'mycontainer', 'report.xlsx')
            raise AssertionError("expected ImportError")
        except ImportError as e:
            assert 'azure' in str(e).lower()


def test_upload_file_uses_connection_string(tmp_path, monkeypatch):
    monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', 'DefaultEndpointsProtocol=https;...')
    monkeypatch.delenv('AZURE_STORAGE_ACCOUNT_KEY', raising=False)
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    blob_mod, service_client, container_client, blob_client = _make_azure_mock()
    with patch.dict(sys.modules, {'azure.storage.blob': blob_mod}):
        from flowforge.storage.azure_blob import upload_file
        url = upload_file(f, 'mycontainer', 'report.xlsx')
    assert url == blob_client.url
    blob_mod.BlobServiceClient.from_connection_string.assert_called_once()
    container_client.upload_blob.assert_called_once()


def test_upload_file_raises_without_any_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv('AZURE_STORAGE_CONNECTION_STRING', raising=False)
    monkeypatch.delenv('AZURE_STORAGE_ACCOUNT_URL', raising=False)
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    blob_mod, service_client, container_client, blob_client = _make_azure_mock()
    with patch.dict(sys.modules, {'azure.storage.blob': blob_mod}):
        from flowforge.storage.azure_blob import upload_file
        try:
            upload_file(f, 'mycontainer', 'report.xlsx')
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert 'AZURE_STORAGE' in str(e)


def test_upload_file_appends_sas_when_shareable_and_key_present(tmp_path, monkeypatch):
    monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', 'conn')
    monkeypatch.setenv('AZURE_STORAGE_ACCOUNT_KEY', 'accountkey123')
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    blob_mod, service_client, container_client, blob_client = _make_azure_mock()
    with patch.dict(sys.modules, {'azure.storage.blob': blob_mod}):
        from flowforge.storage.azure_blob import upload_file
        url = upload_file(f, 'mycontainer', 'report.xlsx', make_shareable=True)
    assert '?sv=2021&sig=abc' in url
    blob_mod.generate_blob_sas.assert_called_once()


def test_upload_file_no_sas_without_account_key(tmp_path, monkeypatch):
    monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', 'conn')
    monkeypatch.delenv('AZURE_STORAGE_ACCOUNT_KEY', raising=False)
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    blob_mod, service_client, container_client, blob_client = _make_azure_mock()
    with patch.dict(sys.modules, {'azure.storage.blob': blob_mod}):
        from flowforge.storage.azure_blob import upload_file
        url = upload_file(f, 'mycontainer', 'report.xlsx', make_shareable=True)
    assert url == blob_client.url
    blob_mod.generate_blob_sas.assert_not_called()


# ── step layer — flowforge/steps/azure_blob_upload.py ───────────────────────────

def test_step_type_is_azure_blob_upload():
    from flowforge.steps.azure_blob_upload import AzureBlobUploadStep
    assert AzureBlobUploadStep.step_type == 'azure_blob_upload'


def test_run_success_returns_drive_url(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.azure_blob_upload import AzureBlobUploadStep
    step = AzureBlobUploadStep(name='upload', config={'file_path': str(f), 'container': 'mycontainer', 'blob_name': 'out.xlsx'})
    with patch('flowforge.storage.azure_blob.upload_file', return_value='https://acct.blob.core.windows.net/mycontainer/out.xlsx') as mock_upload:
        result = step.run({})
    assert result.success is True
    assert result.drive_url == 'https://acct.blob.core.windows.net/mycontainer/out.xlsx'
    mock_upload.assert_called_once()


def test_run_uses_filename_when_no_blob_name_given(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.azure_blob_upload import AzureBlobUploadStep
    step = AzureBlobUploadStep(name='upload', config={'file_path': str(f), 'container': 'c'})
    with patch('flowforge.storage.azure_blob.upload_file', return_value='https://...') as mock_upload:
        step.run({})
    args, _ = mock_upload.call_args
    assert args[2] == 'report.xlsx'


def test_run_renames_file_before_upload(tmp_path):
    f = tmp_path / 'orig.xlsx'
    f.write_text('data')
    from flowforge.steps.azure_blob_upload import AzureBlobUploadStep
    step = AzureBlobUploadStep(name='upload', config={'file_path': str(f), 'container': 'c', 'rename_to': 'renamed.xlsx'})
    with patch('flowforge.storage.azure_blob.upload_file', return_value='https://.../renamed.xlsx'):
        result = step.run({})
    assert result.success is True
    assert (tmp_path / 'renamed.xlsx').exists()
    assert not f.exists()


def test_run_failure_returns_error(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.azure_blob_upload import AzureBlobUploadStep
    step = AzureBlobUploadStep(name='upload', config={'file_path': str(f), 'container': 'c', 'blob_name': 'k'})
    with patch('flowforge.storage.azure_blob.upload_file', side_effect=Exception('auth failed')):
        result = step.run({})
    assert result.success is False
    assert 'auth failed' in result.error
