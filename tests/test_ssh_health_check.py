"""Tests for SshHealthCheckStep."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from flowforge.steps.ssh_health_check import _ALL_METRICS, SshHealthCheckStep

# ── SSH mock helpers ──────────────────────────────────────────────────────────

_LOAD_OUTPUT = "0.42 0.38 0.31 1/234 12345\n4"
_MEMORY_OUTPUT = (
    "              total        used        free      shared  buff/cache   available\n"
    "Mem:           7986        3421        1234         256        3331        4100\n"
    "Swap:          2047           0        2047"
)
_DISK_OUTPUT = (
    "Filesystem      Size  Used Avail Use% Mounted on\n"
    "/dev/sda1        99G   45G   49G  48% /\n"
    "tmpfs           3.9G     0  3.9G   0% /dev/shm"
)
_PS_OUTPUT = (
    "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
    "root         1  0.0  0.0 168944  9552 ?        Ss   May29   0:03 /sbin/init\n"
    "flowforge  123  2.5  1.2 445678 98765 ?        Sl   May29   1:23 python app.py"
)


def _make_conn_mock(outputs: dict[str, str]):
    """Build a conn mock whose exec_command returns the given per-command outputs."""
    conn_mock = MagicMock()
    client_mock = conn_mock.client

    def exec_command(cmd, timeout=30):
        stdin = MagicMock()
        stdout = MagicMock()
        stderr = MagicMock()
        matched = next((v for k, v in outputs.items() if k in cmd), '')
        stdout.read.return_value = matched.encode()
        stdout.channel.recv_exit_status.return_value = 0
        stderr.read.return_value = b''
        return stdin, stdout, stderr

    client_mock.exec_command.side_effect = exec_command
    return conn_mock


_ALL_OUTPUTS = {
    'loadavg': _LOAD_OUTPUT,
    'free':    _MEMORY_OUTPUT,
    'df':      _DISK_OUTPUT,
    'ps':      _PS_OUTPUT,
}


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_all_metrics_collected_by_default(tmp_path):
    step = SshHealthCheckStep(name='health', config={
        'ssh_connection_id': 'conn-1',
    })
    conn_mock = _make_conn_mock(_ALL_OUTPUTS)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert result.output_path
    assert Path(result.output_path).suffix == '.xlsx'
    assert result.rows_affected > 0
    # All four metrics should appear in logs
    for metric_title in ('Load Average', 'Memory', 'Disk Usage', 'Top Processes'):
        assert metric_title in result.logs


def test_selected_metrics_only(tmp_path):
    step = SshHealthCheckStep(name='health', config={
        'ssh_connection_id': 'conn-1',
        'metrics': ['load_average', 'disk_usage'],
    })
    conn_mock = _make_conn_mock(_ALL_OUTPUTS)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert 'Load Average' in result.logs
    assert 'Disk Usage' in result.logs
    assert 'Memory' not in result.logs
    assert 'Top Processes' not in result.logs


def test_csv_format_output(tmp_path):
    step = SshHealthCheckStep(name='health', config={
        'ssh_connection_id': 'conn-1',
        'metrics': ['load_average'],
        'format': 'csv',
    })
    conn_mock = _make_conn_mock(_ALL_OUTPUTS)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert Path(result.output_path).suffix == '.csv'
    content = Path(result.output_path).read_text()
    assert 'Load Average' in content
    assert '0.42' in content


def test_custom_output_filename(tmp_path):
    step = SshHealthCheckStep(name='health', config={
        'ssh_connection_id': 'conn-1',
        'metrics': ['disk_usage'],
        'output_filename': 'disk_{{ current_date }}.xlsx',
    })
    conn_mock = _make_conn_mock(_ALL_OUTPUTS)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert Path(result.output_path).name == 'disk_2026-05-30.xlsx'


def test_missing_connection_id():
    step = SshHealthCheckStep(name='health', config={})
    result = step.run({'steps': {}})
    assert not result.success
    assert 'ssh_connection_id' in result.error


def test_failed_metric_skipped_others_succeed(tmp_path):
    """If one metric command fails, the step still succeeds with the rest."""
    step = SshHealthCheckStep(name='health', config={
        'ssh_connection_id': 'conn-1',
        'metrics': ['load_average', 'memory'],
    })
    conn_mock = MagicMock()
    call_count = [0]

    def exec_command(cmd, timeout=30):
        call_count[0] += 1
        stdin = MagicMock()
        stdout = MagicMock()
        stderr = MagicMock()
        if 'loadavg' in cmd:
            # First metric fails
            stdout.read.return_value = b''
            stdout.channel.recv_exit_status.return_value = 1
            stderr.read.return_value = b'permission denied'
        else:
            stdout.read.return_value = _MEMORY_OUTPUT.encode()
            stdout.channel.recv_exit_status.return_value = 0
            stderr.read.return_value = b''
        return stdin, stdout, stderr

    conn_mock.client.exec_command.side_effect = exec_command

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert 'Memory' in result.logs
    assert 'Load Average' not in result.logs


def test_all_metrics_fail_returns_failure(tmp_path):
    step = SshHealthCheckStep(name='health', config={
        'ssh_connection_id': 'conn-1',
        'metrics': ['load_average'],
    })
    conn_mock = MagicMock()

    def exec_command(cmd, timeout=30):
        stdin, stdout, stderr = MagicMock(), MagicMock(), MagicMock()
        stdout.read.return_value = b''
        stdout.channel.recv_exit_status.return_value = 1
        stderr.read.return_value = b'error'
        return stdin, stdout, stderr

    conn_mock.client.exec_command.side_effect = exec_command

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert not result.success
    assert 'no metrics' in result.error


def test_unknown_metric_skipped_cleanly(tmp_path):
    step = SshHealthCheckStep(name='health', config={
        'ssh_connection_id': 'conn-1',
        'metrics': ['load_average', 'nonexistent_metric'],
    })
    conn_mock = _make_conn_mock(_ALL_OUTPUTS)

    with patch('flowforge.connections.ssh.get_ssh_connection', return_value=conn_mock), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert 'Load Average' in result.logs


def test_step_type_attribute():
    assert SshHealthCheckStep.step_type == 'ssh_health_check'


def test_default_metrics_are_all_four():
    assert set(_ALL_METRICS) == {'load_average', 'memory', 'disk_usage', 'top_processes'}


def test_loader_registers_ssh_health_check():
    from flowforge.engine.loader import _STEP_CLASSES
    assert 'ssh_health_check' in _STEP_CLASSES
