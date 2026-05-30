"""SSH connection implementation using paramiko."""
import logging
import os
import time
from typing import Any

import paramiko

from flowforge.db.models import SSHConnection as SSHConnectionRow, db
from flowforge.crypto import decrypt_config

logger = logging.getLogger(__name__)


class SSHConnection:
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = '',
        password: str = '',
        key_path: str = '',
        key_passphrase: str = '',
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.key_passphrase = key_passphrase
        self.timeout = timeout
        self.client: paramiko.SSHClient | None = None

    def connect(self) -> paramiko.SSHClient:
        """Open an SSH connection. Supports password and private-key auth."""
        ssh = paramiko.SSHClient()
        
        allow_unknown = os.environ.get('FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS', '').lower() == 'true'
        if allow_unknown:
            class _TofuPolicy(paramiko.MissingHostKeyPolicy):
                def missing_host_key(self, client, hostname, key):
                    client._host_keys.add(hostname, key.get_name(), key)
            ssh.set_missing_host_key_policy(_TofuPolicy())
        else:
            ssh.set_missing_host_key_policy(paramiko.RejectPolicy())

        connect_kwargs: dict[str, Any] = {
            'hostname': self.host,
            'port': self.port,
            'username': self.username,
            'timeout': self.timeout,
            'look_for_keys': False,
            'allow_agent': False,
        }
        if self.key_path:
            connect_kwargs['key_filename'] = [self.key_path]
            if self.key_passphrase:
                connect_kwargs['passphrase'] = self.key_passphrase
        else:
            connect_kwargs['password'] = self.password

        try:
            ssh.connect(**connect_kwargs)
            self.client = ssh
            return ssh
        except Exception as exc:
            ssh.close()
            if not allow_unknown and 'not found in known_hosts' in str(exc):
                raise paramiko.SSHException(
                    f"SSH host key rejected for '{self.host}' (strict mode). "
                    f"Add the host key with: ssh-keyscan -H {self.host} >> ~/.ssh/known_hosts"
                    f" or set FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS=true to disable strict checks."
                ) from exc
            raise

    def test(self) -> tuple[bool, int]:
        """Test the connection and return (success, latency_ms)."""
        start = time.monotonic()
        try:
            client = self.connect()
            client.close()
            latency = int((time.monotonic() - start) * 1000)
            return True, latency
        except Exception as e:
            logger.error("SSH connection test failed: %s", e)
            return False, 0

    def close(self):
        if self.client:
            self.client.close()
            self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


def get_ssh_connection(connection_id: str) -> SSHConnection:
    """Return an SSHConnection instance for an ff_ssh_connections row."""
    row = db.session.get(SSHConnectionRow, connection_id)
    if not row:
        raise ValueError(f"SSH connection not found: {connection_id}")

    cfg = decrypt_config(row.config)
    return SSHConnection(
        host=cfg['host'],
        port=int(cfg.get('port', 22)),
        username=cfg['username'],
        password=cfg.get('password', ''),
        key_path=cfg.get('key_path', ''),
        key_passphrase=cfg.get('key_passphrase', ''),
        timeout=int(cfg.get('timeout', 30)),
    )
