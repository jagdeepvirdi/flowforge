"""Tests for flowforge/storage/s3.py and flowforge/steps/s3_upload.py."""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

# ── storage layer — flowforge/storage/s3.py ────────────────────────────────────

def _make_boto3_mock():
    client = MagicMock()
    client.generate_presigned_url.return_value = 'https://bucket.s3.amazonaws.com/key?X-Amz-Signature=abc'
    boto3_mod = ModuleType('boto3')
    boto3_mod.client = MagicMock(return_value=client)
    return boto3_mod, client


def test_upload_file_import_error_when_boto3_missing(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    with patch.dict(sys.modules, {'boto3': None}):
        from flowforge.storage.s3 import upload_file
        try:
            upload_file(f, 'my-bucket', 'report.xlsx')
            raise AssertionError("expected ImportError")
        except ImportError as e:
            assert 's3' in str(e).lower()


def test_upload_file_returns_s3_uri_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv('AWS_ACCESS_KEY_ID', raising=False)
    monkeypatch.delenv('AWS_SECRET_ACCESS_KEY', raising=False)
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    boto3_mod, client = _make_boto3_mock()
    with patch.dict(sys.modules, {'boto3': boto3_mod}):
        from flowforge.storage.s3 import upload_file
        url = upload_file(f, 'my-bucket', 'reports/report.xlsx')
    assert url == 's3://my-bucket/reports/report.xlsx'
    client.upload_file.assert_called_once_with(str(f), 'my-bucket', 'reports/report.xlsx')


def test_upload_file_returns_presigned_url_when_shareable(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    boto3_mod, client = _make_boto3_mock()
    with patch.dict(sys.modules, {'boto3': boto3_mod}):
        from flowforge.storage.s3 import upload_file
        url = upload_file(f, 'my-bucket', 'report.xlsx', make_shareable=True)
    assert url.startswith('https://')
    client.generate_presigned_url.assert_called_once()


def test_get_client_uses_explicit_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIA123')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'eu-west-1')
    boto3_mod, client = _make_boto3_mock()
    with patch.dict(sys.modules, {'boto3': boto3_mod}):
        from flowforge.storage.s3 import _get_client
        _get_client()
    _, kwargs = boto3_mod.client.call_args
    assert kwargs['aws_access_key_id'] == 'AKIA123'
    assert kwargs['aws_secret_access_key'] == 'secret'
    assert kwargs['region_name'] == 'eu-west-1'


# ── step layer — flowforge/steps/s3_upload.py ───────────────────────────────────

def test_step_type_is_s3_upload():
    from flowforge.steps.s3_upload import S3UploadStep
    assert S3UploadStep.step_type == 's3_upload'


def test_run_success_returns_drive_url(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.s3_upload import S3UploadStep
    step = S3UploadStep(name='upload', config={'file_path': str(f), 'bucket': 'my-bucket', 'key': 'out.xlsx'})
    with patch('flowforge.storage.s3.upload_file', return_value='https://bucket.s3.amazonaws.com/out.xlsx') as mock_upload:
        result = step.run({})
    assert result.success is True
    assert result.drive_url == 'https://bucket.s3.amazonaws.com/out.xlsx'
    mock_upload.assert_called_once()


def test_run_uses_filename_when_no_key_given(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.s3_upload import S3UploadStep
    step = S3UploadStep(name='upload', config={'file_path': str(f), 'bucket': 'my-bucket'})
    with patch('flowforge.storage.s3.upload_file', return_value='s3://my-bucket/report.xlsx') as mock_upload:
        step.run({})
    args, _ = mock_upload.call_args
    assert args[2] == 'report.xlsx'


def test_run_renames_file_before_upload(tmp_path):
    f = tmp_path / 'orig.xlsx'
    f.write_text('data')
    from flowforge.steps.s3_upload import S3UploadStep
    step = S3UploadStep(name='upload', config={'file_path': str(f), 'bucket': 'b', 'rename_to': 'renamed.xlsx'})
    with patch('flowforge.storage.s3.upload_file', return_value='s3://b/renamed.xlsx') as mock_upload:
        result = step.run({})
    assert result.success is True
    assert (tmp_path / 'renamed.xlsx').exists()
    assert not f.exists()
    args, _ = mock_upload.call_args
    assert args[0].name == 'renamed.xlsx'


def test_run_failure_returns_error(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.s3_upload import S3UploadStep
    step = S3UploadStep(name='upload', config={'file_path': str(f), 'bucket': 'b', 'key': 'k'})
    with patch('flowforge.storage.s3.upload_file', side_effect=Exception('access denied')):
        result = step.run({})
    assert result.success is False
    assert 'access denied' in result.error


def test_run_presigned_url_default_true(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.s3_upload import S3UploadStep
    step = S3UploadStep(name='upload', config={'file_path': str(f), 'bucket': 'b', 'key': 'k'})
    with patch('flowforge.storage.s3.upload_file', return_value='https://...') as mock_upload:
        step.run({})
    _, kwargs = mock_upload.call_args
    assert kwargs['make_shareable'] is True


def test_run_presigned_url_can_be_disabled(tmp_path):
    f = tmp_path / 'report.xlsx'
    f.write_text('data')
    from flowforge.steps.s3_upload import S3UploadStep
    step = S3UploadStep(name='upload', config={'file_path': str(f), 'bucket': 'b', 'key': 'k', 'presigned_url': False})
    with patch('flowforge.storage.s3.upload_file', return_value='s3://b/k') as mock_upload:
        step.run({})
    _, kwargs = mock_upload.call_args
    assert kwargs['make_shareable'] is False
