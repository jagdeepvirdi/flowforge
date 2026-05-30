"""Tests for SshCommandStep."""
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
