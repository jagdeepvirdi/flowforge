"""Tests for SftpTransferStep."""
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flowforge.steps.sftp_transfer import (
    SftpTransferStep,
    _mkdir_remote,
    _remote_is_dir,
    _sftp_connect,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _step(operation='download', **extra):
    cfg = {
        'host': 'sftp.example.com',
        'username': 'user',
        'password': 'secret',
        'operation': operation,
        'remote_path': '/remote/file.csv',
        'local_path': '/local/file.csv',
    }
    cfg.update(extra)
    return SftpTransferStep(name='sftp', config=cfg)


def _make_sftp_entry(name, is_dir=False):
    entry = MagicMock()
    entry.filename = name
    mode = stat.S_IFDIR | 0o755 if is_dir else stat.S_IFREG | 0o644
    entry.st_mode = mode
    return entry


# ── _sftp_connect ─────────────────────────────────────────────────────────────

def test_sftp_connect_raises_import_error_without_paramiko():
    with patch.dict('sys.modules', {'paramiko': None}):
        import importlib

        import flowforge.steps.sftp_transfer as m
        importlib.reload(m)
        with pytest.raises(ImportError, match='paramiko'):
            with m._sftp_connect('host', 22, 'user', password='pw'):
                pass
    # reload without the patch so the module is back to normal
    importlib.reload(m)


def test_sftp_connect_raises_value_error_without_credentials():
    with pytest.raises(ValueError, match='password or key_path'):
        with _sftp_connect('host', 22, 'user'):
            pass


def test_sftp_connect_uses_password(tmp_path):
    paramiko_mock = MagicMock()
    ssh_mock = paramiko_mock.SSHClient.return_value
    sftp_mock = ssh_mock.open_sftp.return_value

    with patch.dict('sys.modules', {'paramiko': paramiko_mock}):
        with _sftp_connect('host', 22, 'user', password='pw') as sftp:
            assert sftp is sftp_mock

    ssh_mock.connect.assert_called_once()
    call_kwargs = ssh_mock.connect.call_args[1]
    assert call_kwargs['password'] == 'pw'
    assert 'key_filename' not in call_kwargs
    ssh_mock.close.assert_called_once()
    sftp_mock.close.assert_called_once()


def test_sftp_connect_uses_key_path():
    paramiko_mock = MagicMock()
    ssh_mock = paramiko_mock.SSHClient.return_value

    with patch.dict('sys.modules', {'paramiko': paramiko_mock}):
        with _sftp_connect('host', 22, 'user', key_path='/home/user/.ssh/id_rsa') as _sftp:
            pass

    call_kwargs = ssh_mock.connect.call_args[1]
    assert call_kwargs['key_filename'] == ['/home/user/.ssh/id_rsa']
    assert 'password' not in call_kwargs


def test_sftp_connect_passes_key_passphrase():
    paramiko_mock = MagicMock()
    ssh_mock = paramiko_mock.SSHClient.return_value

    with patch.dict('sys.modules', {'paramiko': paramiko_mock}):
        with _sftp_connect('host', 22, 'user', key_path='/k', key_passphrase='phrase') as _:
            pass

    call_kwargs = ssh_mock.connect.call_args[1]
    assert call_kwargs['passphrase'] == 'phrase'


def test_sftp_connect_passes_custom_port_and_timeout():
    paramiko_mock = MagicMock()
    ssh_mock = paramiko_mock.SSHClient.return_value

    with patch.dict('sys.modules', {'paramiko': paramiko_mock}):
        with _sftp_connect('host', 2222, 'user', password='pw', timeout=60) as _:
            pass

    kw = ssh_mock.connect.call_args[1]
    assert kw['port'] == 2222
    assert kw['timeout'] == 60


# ── _mkdir_remote ─────────────────────────────────────────────────────────────

def test_mkdir_remote_creates_nested_dirs():
    sftp = MagicMock()
    sftp.stat.side_effect = OSError('not found')

    _mkdir_remote(sftp, '/a/b/c')

    assert sftp.mkdir.call_count == 3
    sftp.mkdir.assert_any_call('/a')
    sftp.mkdir.assert_any_call('/a/b')
    sftp.mkdir.assert_any_call('/a/b/c')


def test_mkdir_remote_skips_existing():
    sftp = MagicMock()
    sftp.stat.return_value = MagicMock()  # no OSError → dir exists

    _mkdir_remote(sftp, '/a/b')

    sftp.mkdir.assert_not_called()


def test_mkdir_remote_relative_path():
    sftp = MagicMock()
    sftp.stat.side_effect = OSError

    _mkdir_remote(sftp, 'uploads/data')

    sftp.mkdir.assert_any_call('/uploads')
    sftp.mkdir.assert_any_call('/uploads/data')


# ── _remote_is_dir ────────────────────────────────────────────────────────────

def test_remote_is_dir_true():
    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFDIR | 0o755
    assert _remote_is_dir(sftp, '/some/dir') is True


def test_remote_is_dir_false():
    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFREG | 0o644
    assert _remote_is_dir(sftp, '/some/file.txt') is False


# ── Step: validation ──────────────────────────────────────────────────────────

def test_step_missing_host_returns_error():
    step = SftpTransferStep(name='s', config={
        'username': 'u', 'password': 'p', 'operation': 'download',
        'remote_path': '/r', 'local_path': '/l',
    })
    result = step.run({'steps': {}})
    assert not result.success
    assert 'host' in result.error


def test_step_missing_username_returns_error():
    step = SftpTransferStep(name='s', config={
        'host': 'h', 'password': 'p', 'operation': 'download',
        'remote_path': '/r', 'local_path': '/l',
    })
    result = step.run({'steps': {}})
    assert not result.success
    assert 'username' in result.error


def test_step_invalid_operation_returns_error():
    step = _step(operation='copy')
    result = step.run({'steps': {}})
    assert not result.success
    assert 'operation' in result.error


def test_step_missing_remote_path_returns_error():
    step = SftpTransferStep(name='s', config={
        'host': 'h', 'username': 'u', 'password': 'p',
        'operation': 'download', 'remote_path': '', 'local_path': '/l',
    })
    result = step.run({'steps': {}})
    assert not result.success
    assert 'remote_path' in result.error


def test_step_missing_local_path_returns_error():
    step = SftpTransferStep(name='s', config={
        'host': 'h', 'username': 'u', 'password': 'p',
        'operation': 'download', 'remote_path': '/r', 'local_path': '',
    })
    result = step.run({'steps': {}})
    assert not result.success
    assert 'local_path' in result.error


# ── Step: paramiko not installed ──────────────────────────────────────────────

def test_step_paramiko_not_installed_returns_failure():
    step = _step()
    with patch('flowforge.steps.sftp_transfer._sftp_connect',
               side_effect=ImportError('pip install paramiko')):
        result = step.run({'steps': {}})
    assert not result.success
    assert 'paramiko' in result.error


# ── Step: download single file ────────────────────────────────────────────────

def test_download_file_happy_path(tmp_path):
    local_file = tmp_path / 'file.csv'
    step = _step(local_path=str(local_file))

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFREG | 0o644

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        # Simulate sftp.get writing the file
        sftp.get.side_effect = lambda remote, local: Path(local).write_text('data')
        result = step.run({'steps': {}})

    assert result.success
    assert result.files_found == 1
    assert result.files_loaded == 1
    assert result.output_path == str(local_file)
    sftp.get.assert_called_once_with('/remote/file.csv', str(local_file))


def test_download_file_skips_when_overwrite_false(tmp_path):
    local_file = tmp_path / 'file.csv'
    local_file.write_text('existing')
    step = _step(local_path=str(local_file), overwrite=False)

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFREG | 0o644

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.success
    assert result.files_loaded == 0
    sftp.get.assert_not_called()


def test_download_file_remote_not_found_returns_error():
    step = _step()
    sftp = MagicMock()
    sftp.stat.side_effect = OSError('no such file')

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert not result.success
    assert 'not found' in result.error.lower()


def test_download_file_places_inside_dir_when_local_is_directory(tmp_path):
    step = _step(remote_path='/remote/report.xlsx', local_path=str(tmp_path))

    sftp = MagicMock()
    # First stat call checks if remote is dir → it's a file
    sftp.stat.return_value.st_mode = stat.S_IFREG | 0o644
    sftp.get.side_effect = lambda r, loc: Path(loc).write_text('x')

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.success
    assert result.output_path == str(tmp_path / 'report.xlsx')


# ── Step: download directory ──────────────────────────────────────────────────

def test_download_directory_downloads_all_files(tmp_path):
    step = _step(remote_path='/remote/dir', local_path=str(tmp_path))

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFDIR | 0o755
    entries = [_make_sftp_entry('a.csv'), _make_sftp_entry('b.csv')]
    sftp.listdir_attr.return_value = entries
    sftp.get.side_effect = lambda r, loc: Path(loc).write_text('data')

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.success
    assert result.files_found == 2
    assert result.files_loaded == 2
    assert result.files_failed == 0


def test_download_directory_applies_glob_pattern(tmp_path):
    step = _step(remote_path='/remote/dir', local_path=str(tmp_path), pattern='*.csv')

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFDIR | 0o755
    entries = [_make_sftp_entry('data.csv'), _make_sftp_entry('notes.txt')]
    sftp.listdir_attr.return_value = entries
    sftp.get.side_effect = lambda r, loc: Path(loc).write_text('x')

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.files_found == 1
    assert result.files_loaded == 1
    sftp.get.assert_called_once()
    assert 'data.csv' in sftp.get.call_args[0][0]


def test_download_directory_skips_subdirectories(tmp_path):
    step = _step(remote_path='/remote/dir', local_path=str(tmp_path))

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFDIR | 0o755
    entries = [_make_sftp_entry('file.csv'), _make_sftp_entry('subdir', is_dir=True)]
    sftp.listdir_attr.return_value = entries
    sftp.get.side_effect = lambda r, loc: Path(loc).write_text('x')

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.files_found == 1
    assert result.files_loaded == 1


def test_download_directory_partial_failure(tmp_path):
    step = _step(remote_path='/remote/dir', local_path=str(tmp_path))

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFDIR | 0o755
    entries = [_make_sftp_entry('ok.csv'), _make_sftp_entry('bad.csv')]
    sftp.listdir_attr.return_value = entries

    def _get(remote, local):
        if 'bad' in remote:
            raise OSError('permission denied')
        Path(local).write_text('data')

    sftp.get.side_effect = _get

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert not result.success
    assert result.files_loaded == 1
    assert result.files_failed == 1
    assert 'bad.csv' in result.logs


def test_download_directory_overwrite_false_skips_existing(tmp_path):
    existing = tmp_path / 'existing.csv'
    existing.write_text('old')
    step = _step(remote_path='/remote/dir', local_path=str(tmp_path), overwrite=False)

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFDIR | 0o755
    sftp.listdir_attr.return_value = [_make_sftp_entry('existing.csv')]

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.success
    assert result.files_loaded == 0
    sftp.get.assert_not_called()


# ── Step: upload ──────────────────────────────────────────────────────────────

def test_upload_happy_path(tmp_path):
    local_file = tmp_path / 'report.xlsx'
    local_file.write_bytes(b'x' * 1024)
    step = _step(operation='upload', local_path=str(local_file), remote_path='/remote/report.xlsx')

    sftp = MagicMock()
    sftp.stat.side_effect = OSError  # remote doesn't exist yet

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.success
    assert result.files_loaded == 1
    sftp.put.assert_called_once_with(str(local_file), '/remote/report.xlsx')


def test_upload_appends_filename_when_remote_ends_with_slash(tmp_path):
    local_file = tmp_path / 'data.csv'
    local_file.write_text('a,b')
    step = _step(operation='upload', local_path=str(local_file), remote_path='/remote/')

    sftp = MagicMock()
    sftp.stat.side_effect = OSError

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        step.run({'steps': {}})

    sftp.put.assert_called_once_with(str(local_file), '/remote/data.csv')


def test_upload_local_file_not_found_returns_error():
    step = _step(operation='upload', local_path='/nonexistent/file.csv', remote_path='/remote/f.csv')
    result = step.run({'steps': {}})
    assert not result.success
    assert 'not found' in result.error.lower()


def test_upload_local_path_is_directory_returns_error(tmp_path):
    step = _step(operation='upload', local_path=str(tmp_path), remote_path='/remote/f.csv')
    result = step.run({'steps': {}})
    assert not result.success
    assert 'not a file' in result.error.lower()


def test_upload_skips_when_remote_exists_and_overwrite_false(tmp_path):
    local_file = tmp_path / 'f.csv'
    local_file.write_text('data')
    step = _step(operation='upload', local_path=str(local_file), remote_path='/remote/f.csv', overwrite=False)

    sftp = MagicMock()
    sftp.stat.return_value = MagicMock()  # remote exists

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert result.success
    assert result.files_loaded == 0
    sftp.put.assert_not_called()


def test_upload_creates_remote_dirs_by_default(tmp_path):
    local_file = tmp_path / 'f.csv'
    local_file.write_text('data')
    step = _step(operation='upload', local_path=str(local_file), remote_path='/new/dir/f.csv')

    sftp = MagicMock()
    sftp.stat.side_effect = OSError

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx, \
         patch('flowforge.steps.sftp_transfer._mkdir_remote') as mock_mkdir:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        step.run({'steps': {}})

    mock_mkdir.assert_called_once_with(sftp, '/new/dir')


def test_upload_skips_mkdir_when_create_remote_dirs_false(tmp_path):
    local_file = tmp_path / 'f.csv'
    local_file.write_text('data')
    step = _step(
        operation='upload', local_path=str(local_file),
        remote_path='/remote/f.csv', create_remote_dirs=False,
    )

    sftp = MagicMock()
    sftp.stat.side_effect = OSError

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx, \
         patch('flowforge.steps.sftp_transfer._mkdir_remote') as mock_mkdir:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        step.run({'steps': {}})

    mock_mkdir.assert_not_called()


def test_upload_mkdir_failure_returns_error(tmp_path):
    local_file = tmp_path / 'f.csv'
    local_file.write_text('data')
    step = _step(operation='upload', local_path=str(local_file), remote_path='/bad/f.csv')

    sftp = MagicMock()
    sftp.stat.side_effect = OSError

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx, \
         patch('flowforge.steps.sftp_transfer._mkdir_remote', side_effect=OSError('permission denied')):
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run({'steps': {}})

    assert not result.success
    assert 'remote directory' in result.error.lower()


# ── Step: general error handling ──────────────────────────────────────────────

def test_step_generic_exception_returns_failure():
    step = _step()
    with patch('flowforge.steps.sftp_transfer._sftp_connect', side_effect=Exception('timeout')):
        result = step.run({'steps': {}})
    assert not result.success
    assert 'SFTP error' in result.error


# ── Jinja2 variable rendering ─────────────────────────────────────────────────

def test_step_renders_jinja_in_remote_path(tmp_path):
    """Remote and local paths support {{ variable }} rendering."""
    from flowforge.engine.context import build
    ctx = build('test')
    month = ctx['current_month']

    _local_file = tmp_path / f'report_{month}.csv'
    step = SftpTransferStep(name='sftp', config={
        'host': 'h', 'username': 'u', 'password': 'p',
        'operation': 'download',
        'remote_path': '/reports/report_{{ current_month }}.csv',
        'local_path': str(tmp_path / 'report_{{ current_month }}.csv'),
    })

    sftp = MagicMock()
    sftp.stat.return_value.st_mode = stat.S_IFREG | 0o644
    sftp.get.side_effect = lambda r, loc: Path(loc).write_text('x')

    with patch('flowforge.steps.sftp_transfer._sftp_connect') as mock_ctx:
        mock_ctx.return_value.__enter__ = lambda s: sftp
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = step.run(ctx)

    called_remote = sftp.get.call_args[0][0]
    assert '{{' not in called_remote
    assert month in called_remote
    assert result.success


# ── Step attributes ───────────────────────────────────────────────────────────

def test_step_type_attribute():
    step = SftpTransferStep(name='s', config={})
    assert step.step_type == 'sftp_transfer'


# ── Loader registration ───────────────────────────────────────────────────────

def test_loader_registers_sftp_transfer():
    from flowforge.engine.loader import _STEP_CLASSES
    assert 'sftp_transfer' in _STEP_CLASSES
    assert 'SftpTransferStep' in _STEP_CLASSES['sftp_transfer']
