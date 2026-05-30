"""Tests for SshCommandStep."""
from unittest.mock import MagicMock, patch

from flowforge.steps.ssh_command import SshCommandStep


def test_ssh_command_happy_path():
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'echo "hello"',
    }
    step = SshCommandStep(name='ssh', config=config)
    
    conn_mock = MagicMock()
    ssh_client_mock = conn_mock.client
    stdout_mock = ssh_client_mock.exec_command.return_value[1]
    stdout_mock.read.return_value = b"hello\n"
    stdout_mock.channel.recv_exit_status.return_value = 0
    stderr_mock = ssh_client_mock.exec_command.return_value[2]
    stderr_mock.read.return_value = b""

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
    
    conn_mock = MagicMock()
    ssh_client_mock = conn_mock.client
    stdout_mock = ssh_client_mock.exec_command.return_value[1]
    stdout_mock.read.return_value = b""
    stdout_mock.channel.recv_exit_status.return_value = 2
    stderr_mock = ssh_client_mock.exec_command.return_value[2]
    stderr_mock.read.return_value = b"ls: /nonexistent: No such file or directory\n"

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock):
        result = step.run({'steps': {}})

    assert not result.success
    assert "Exit status: 2" in result.logs
    assert "No such file or directory" in result.logs


def test_ssh_command_output_var():
    config = {
        'ssh_connection_id': 'conn-123',
        'command': 'whoami',
        'output_var': 'remote_user'
    }
    step = SshCommandStep(name='ssh', config=config)
    
    conn_mock = MagicMock()
    ssh_client_mock = conn_mock.client
    stdout_mock = ssh_client_mock.exec_command.return_value[1]
    stdout_mock.read.return_value = b"root\n"
    stdout_mock.channel.recv_exit_status.return_value = 0

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
    
    conn_mock = MagicMock()
    ssh_client_mock = conn_mock.client
    stdout_mock = ssh_client_mock.exec_command.return_value[1]
    stdout_mock.read.return_value = b"2026-05-30\n"
    stdout_mock.channel.recv_exit_status.return_value = 0

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock):
        step.run({'current_date': '2026-05-30', 'steps': {}})

    ssh_client_mock.exec_command.assert_called_once_with('echo "2026-05-30"', timeout=60)
