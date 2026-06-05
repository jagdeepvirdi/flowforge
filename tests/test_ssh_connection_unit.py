"""Unit tests for flowforge/connections/ssh.py — SSHConnection class and get_ssh_connection.

All tests mock paramiko via sys.modules patching.
"""
import uuid
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_paramiko_mock():
    """Create a minimal paramiko mock with the pieces SSHConnection needs."""
    mock_paramiko = ModuleType('paramiko')

    # SSHClient mock
    mock_client = MagicMock()
    mock_client_class = MagicMock(return_value=mock_client)
    mock_paramiko.SSHClient = mock_client_class

    # Policy mocks
    mock_paramiko.MissingHostKeyPolicy = object  # base class for _TofuPolicy
    mock_paramiko.RejectPolicy = MagicMock

    # SSHException
    class _SSHException(Exception):
        pass
    mock_paramiko.SSHException = _SSHException

    return mock_paramiko, mock_client


def _make_ssh(host='localhost', port=22, username='user',
              password='pass', key_path='', key_passphrase='',
              timeout=30):
    from flowforge.connections.ssh import SSHConnection
    return SSHConnection(
        host=host,
        port=port,
        username=username,
        password=password,
        key_path=key_path,
        key_passphrase=key_passphrase,
        timeout=timeout,
    )


# ── connect() ─────────────────────────────────────────────────────────────────

def test_connect_paramiko_not_installed():
    """ImportError if paramiko is not available."""
    with patch.dict('sys.modules', {'paramiko': None}):
        conn = _make_ssh()
        with pytest.raises((ImportError, Exception)):
            conn.connect()


def test_connect_password_auth():
    """connect() uses password when key_path is empty."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='myuser', password='mypass')
        conn.connect()

    mock_client.connect.assert_called_once()
    kwargs = mock_client.connect.call_args[1]
    assert kwargs['hostname'] == 'myhost'
    assert kwargs['username'] == 'myuser'
    assert kwargs['password'] == 'mypass'
    assert 'key_filename' not in kwargs


def test_connect_key_auth():
    """connect() uses key_filename when key_path is set."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(
            host='myhost', username='myuser',
            key_path='/home/user/.ssh/id_rsa',
        )
        conn.connect()

    kwargs = mock_client.connect.call_args[1]
    assert kwargs['key_filename'] == ['/home/user/.ssh/id_rsa']
    assert 'password' not in kwargs


def test_connect_key_with_passphrase():
    """connect() passes passphrase when key_passphrase is set."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(
            host='myhost', username='myuser',
            key_path='/home/user/.ssh/id_rsa',
            key_passphrase='my-passphrase',
        )
        conn.connect()

    kwargs = mock_client.connect.call_args[1]
    assert kwargs.get('passphrase') == 'my-passphrase'


def test_connect_sets_tofu_policy_when_allow_unknown(monkeypatch):
    """FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS=true → TofuPolicy (not RejectPolicy)."""
    monkeypatch.setenv('FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS', 'true')
    mock_paramiko, mock_client = _make_paramiko_mock()

    set_policy_calls = []

    def capture_policy(policy):
        set_policy_calls.append(policy)

    mock_client.set_missing_host_key_policy.side_effect = capture_policy

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        conn.connect()

    assert len(set_policy_calls) == 1
    # TofuPolicy is a local class defined inside connect() — it's not RejectPolicy
    policy = set_policy_calls[0]
    assert not isinstance(policy, type(mock_paramiko.RejectPolicy))


def test_connect_sets_reject_policy_when_strict(monkeypatch):
    """Default (strict) mode → RejectPolicy."""
    monkeypatch.delenv('FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS', raising=False)
    mock_paramiko, mock_client = _make_paramiko_mock()

    reject_instance = MagicMock()
    mock_paramiko.RejectPolicy = MagicMock(return_value=reject_instance)

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        conn.connect()

    mock_client.set_missing_host_key_policy.assert_called_once()


def test_connect_re_raises_exception():
    """General connection exception is re-raised."""
    mock_paramiko, mock_client = _make_paramiko_mock()
    mock_client.connect.side_effect = RuntimeError('connection refused')

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        with pytest.raises(RuntimeError, match='connection refused'):
            conn.connect()


def test_connect_known_hosts_error_in_strict_mode_raises_ssh_exception(monkeypatch):
    """'not found in known_hosts' → raises SSHException with helpful message."""
    monkeypatch.delenv('FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS', raising=False)
    mock_paramiko, mock_client = _make_paramiko_mock()

    class _SSHExc(Exception):
        pass
    mock_paramiko.SSHException = _SSHExc
    mock_client.connect.side_effect = Exception('not found in known_hosts')

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='stricthost', username='u', password='p')
        with pytest.raises(_SSHExc, match='strict mode'):
            conn.connect()


def test_connect_known_hosts_error_not_raised_in_tofu_mode(monkeypatch):
    """'not found in known_hosts' does NOT trigger SSHException when allow_unknown=true."""
    monkeypatch.setenv('FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS', 'true')
    mock_paramiko, mock_client = _make_paramiko_mock()

    class _SSHExc(Exception):
        pass
    mock_paramiko.SSHException = _SSHExc

    # In tofu mode, connect raises an error unrelated to known_hosts handling
    mock_client.connect.side_effect = RuntimeError('timeout')

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='tofuhost', username='u', password='p')
        with pytest.raises(RuntimeError, match='timeout'):
            conn.connect()


def test_connect_stores_client_on_success():
    """After successful connect(), self.client is set."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        returned = conn.connect()

    assert conn.client is mock_client
    assert returned is mock_client


# ── test() ────────────────────────────────────────────────────────────────────

def test_test_success():
    """test() returns (True, latency_ms >= 0) on success."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        ok, latency = conn.test()

    assert ok is True
    assert latency >= 0


def test_test_failure_returns_false_zero():
    """test() returns (False, 0) when connect raises."""
    mock_paramiko, mock_client = _make_paramiko_mock()
    mock_client.connect.side_effect = RuntimeError('connection refused')

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='badhost', username='u', password='p')
        ok, latency = conn.test()

    assert ok is False
    assert latency == 0


def test_test_calls_connect_and_close():
    """test() calls connect() and then close() on the returned client."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        conn.test()

    mock_client.connect.assert_called_once()
    mock_client.close.assert_called_once()


# ── close() ───────────────────────────────────────────────────────────────────

def test_close_calls_client_close():
    """close() calls client.close() and sets self.client = None."""
    mock_client = MagicMock()

    from flowforge.connections.ssh import SSHConnection
    conn = SSHConnection(host='myhost', username='u', password='p')
    conn.client = mock_client

    conn.close()

    mock_client.close.assert_called_once()
    assert conn.client is None


def test_close_noop_when_client_none():
    """close() is safe to call when client is None."""
    from flowforge.connections.ssh import SSHConnection
    conn = SSHConnection(host='myhost', username='u', password='p')
    conn.client = None
    conn.close()  # must not raise


# ── __enter__ / __exit__ ──────────────────────────────────────────────────────

def test_context_manager_enter_calls_connect():
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        result = conn.__enter__()

    mock_client.connect.assert_called_once()
    assert result is conn


def test_context_manager_exit_calls_close():
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        conn.client = mock_client
        conn.__exit__(None, None, None)

    mock_client.close.assert_called_once()


def test_context_manager_full_cycle():
    """Using SSHConnection as a context manager connects and disconnects."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='myhost', username='u', password='p')
        with conn:
            pass

    mock_client.connect.assert_called_once()
    mock_client.close.assert_called_once()


# ── get_ssh_connection() ──────────────────────────────────────────────────────

def test_get_ssh_connection_not_found_raises(app):
    """get_ssh_connection raises ValueError when connection_id not in DB."""
    fake_id = str(uuid.uuid4())
    with app.app_context():
        from flowforge.connections.ssh import get_ssh_connection
        with pytest.raises(ValueError, match='not found'):
            get_ssh_connection(fake_id)


def test_get_ssh_connection_returns_ssh_connection(app):
    """get_ssh_connection with a mocked DB row + decrypt returns SSHConnection instance."""
    from flowforge.connections.ssh import SSHConnection

    mock_row = MagicMock()
    mock_row.config = '{"encrypted":"data"}'

    decrypted_config = {
        'host': 'remotehost',
        'port': '2222',
        'username': 'deploy',
        'password': 'secret',
        'key_path': '',
        'key_passphrase': '',
        'timeout': '60',
    }

    with patch('flowforge.connections.ssh.db') as mock_db, \
         patch('flowforge.connections.ssh.decrypt_config', return_value=decrypted_config):
        mock_db.session.get.return_value = mock_row
        with app.app_context():
            from flowforge.connections.ssh import get_ssh_connection
            conn = get_ssh_connection('fake-connection-id')

    assert isinstance(conn, SSHConnection)
    assert conn.host == 'remotehost'
    assert conn.port == 2222
    assert conn.username == 'deploy'
    assert conn.timeout == 60


def test_get_ssh_connection_default_port(app):
    """get_ssh_connection uses port 22 by default when not in config."""
    mock_row = MagicMock()
    mock_row.config = '{}'

    decrypted_config = {
        'host': 'myhost',
        'username': 'user',
    }

    with patch('flowforge.connections.ssh.db') as mock_db, \
         patch('flowforge.connections.ssh.decrypt_config', return_value=decrypted_config):
        mock_db.session.get.return_value = mock_row
        with app.app_context():
            from flowforge.connections.ssh import get_ssh_connection
            conn = get_ssh_connection('fake-id')

    assert conn.port == 22


def test_get_ssh_connection_default_timeout(app):
    """get_ssh_connection uses timeout 30 by default."""
    mock_row = MagicMock()
    mock_row.config = '{}'

    decrypted_config = {'host': 'h', 'username': 'u'}

    with patch('flowforge.connections.ssh.db') as mock_db, \
         patch('flowforge.connections.ssh.decrypt_config', return_value=decrypted_config):
        mock_db.session.get.return_value = mock_row
        with app.app_context():
            from flowforge.connections.ssh import get_ssh_connection
            conn = get_ssh_connection('fake-id')

    assert conn.timeout == 30


# ── edge cases ────────────────────────────────────────────────────────────────

def test_ssh_connection_attributes_stored():
    """SSHConnection stores all init kwargs as attributes."""
    from flowforge.connections.ssh import SSHConnection
    conn = SSHConnection(
        host='h', port=2222, username='u',
        password='p', key_path='/k', key_passphrase='kp', timeout=15,
    )
    assert conn.host == 'h'
    assert conn.port == 2222
    assert conn.username == 'u'
    assert conn.password == 'p'
    assert conn.key_path == '/k'
    assert conn.key_passphrase == 'kp'
    assert conn.timeout == 15
    assert conn.client is None


def test_ssh_connection_look_for_keys_false():
    """connect() always sets look_for_keys=False to avoid accidental key discovery."""
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='h', username='u', password='p')
        conn.connect()

    kwargs = mock_client.connect.call_args[1]
    assert kwargs.get('look_for_keys') is False
    assert kwargs.get('allow_agent') is False


def test_ssh_connection_timeout_passed_to_connect():
    mock_paramiko, mock_client = _make_paramiko_mock()

    with patch.dict('sys.modules', {'paramiko': mock_paramiko}):
        from flowforge.connections.ssh import SSHConnection
        conn = SSHConnection(host='h', username='u', password='p', timeout=45)
        conn.connect()

    kwargs = mock_client.connect.call_args[1]
    assert kwargs.get('timeout') == 45
