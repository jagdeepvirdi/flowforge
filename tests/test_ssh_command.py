"""Tests for SshCommandStep."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from flowforge.steps.ssh_command import SshCommandStep


def _make_ssh_mocks(stdout_bytes=b"", stderr_bytes=b"", exit_status=0):
    """Return (conn_mock, ssh_client_mock) with exec_command wired up as a 3-tuple."""
    conn_mock = MagicMock()
    ssh_client_mock = conn_mock.client

    stdin_mock = MagicMock()
    stdout_mock = MagicMock()
    stderr_mock = MagicMock()

    stdout_mock.read.return_value = stdout_bytes
    stdout_mock.channel.recv_exit_status.return_value = exit_status
    stderr_mock.read.return_value = stderr_bytes

    ssh_client_mock.exec_command.return_value = (stdin_mock, stdout_mock, stderr_mock)
    return conn_mock, ssh_client_mock


def test_ssh_command_happy_path():
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'echo "hello"',
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, ssh_client_mock = _make_ssh_mocks(stdout_bytes=b"hello\n", exit_status=0)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock):
        result = step.run({'steps': {}})

    assert result.success
    assert "hello" in result.logs
    assert "Exit status: 0" in result.logs
    ssh_client_mock.exec_command.assert_called_once_with('echo "hello"', timeout=60)


def test_ssh_command_failure():
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'ls /nonexistent',
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, ssh_client_mock = _make_ssh_mocks(
        stderr_bytes=b"ls: /nonexistent: No such file or directory\n",
        exit_status=2,
    )

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock):
        result = step.run({'steps': {}})

    assert not result.success
    assert "Exit status: 2" in result.logs
    assert "No such file or directory" in result.logs


def test_ssh_command_output_var():
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'whoami',
        'output_var': 'remote_user',
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, _ = _make_ssh_mocks(stdout_bytes=b"root\n", exit_status=0)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock):
        result = step.run({'steps': {}})

    assert result.success
    assert result.output_variables == {'remote_user': 'root'}


def test_ssh_command_renders_jinja():
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'echo "{{ current_date }}"',
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, ssh_client_mock = _make_ssh_mocks(stdout_bytes=b"2026-05-30\n", exit_status=0)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock):
        step.run({'current_date': '2026-05-30', 'steps': {}})

    ssh_client_mock.exec_command.assert_called_once_with('echo "2026-05-30"', timeout=60)


# ── save_output tests ─────────────────────────────────────────────────────────

def test_save_output_creates_file(tmp_path):
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'python /scripts/extract.py',
        'save_output': True,
    }
    step = SshCommandStep(name='extract', config=config)
    conn_mock, _ = _make_ssh_mocks(stdout_bytes=b"Processed 1234 records\nDone.", exit_status=0)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert result.output_path
    path = Path(result.output_path)
    assert path.exists()
    assert '1234 records' in path.read_text()


def test_save_output_default_filename_uses_log_extension(tmp_path):
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'uptime',
        'save_output': True,
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, _ = _make_ssh_mocks(stdout_bytes=b"up 3 days", exit_status=0)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert Path(result.output_path).suffix == '.log'


def test_save_output_custom_filename(tmp_path):
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'uptime',
        'save_output': True,
        'output_filename': 'extract_{{ current_date }}.txt',
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, _ = _make_ssh_mocks(stdout_bytes=b"done", exit_status=0)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert Path(result.output_path).name == 'extract_2026-05-30.txt'


def test_save_output_includes_stderr_by_default(tmp_path):
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'myscript.sh',
        'save_output': True,
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, _ = _make_ssh_mocks(
        stdout_bytes=b"stdout line",
        stderr_bytes=b"warning: something",
        exit_status=0,
    )

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    content = Path(result.output_path).read_text()
    assert 'stdout line' in content
    assert 'warning: something' in content
    assert 'STDERR' in content


def test_save_output_exclude_stderr(tmp_path):
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'myscript.sh',
        'save_output': True,
        'include_stderr': False,
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, _ = _make_ssh_mocks(
        stdout_bytes=b"stdout only",
        stderr_bytes=b"this should not appear",
        exit_status=0,
    )

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    content = Path(result.output_path).read_text()
    assert 'stdout only' in content
    assert 'this should not appear' not in content


def test_save_output_false_sets_no_output_path():
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'uptime',
        'save_output': False,
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, _ = _make_ssh_mocks(stdout_bytes=b"up 3 days", exit_status=0)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock):
        result = step.run({'steps': {}})

    assert result.success
    assert not result.output_path


def test_save_output_set_on_failed_command(tmp_path):
    """output_path is set even when the command exits non-zero, so the log can be attached."""
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'failing_script.sh',
        'save_output': True,
    }
    step = SshCommandStep(name='ssh', config=config)
    conn_mock, _ = _make_ssh_mocks(
        stdout_bytes=b"partial output before crash",
        stderr_bytes=b"error: segfault",
        exit_status=1,
    )

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert not result.success
    assert result.output_path               # file still saved despite failure
    assert Path(result.output_path).exists()
