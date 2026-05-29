"""SFTP transfer step — download files from or upload files to a remote SFTP server."""
import contextlib
import fnmatch
import logging
import os
import stat as stat_module
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)

_VALID_OPERATIONS = {'download', 'upload'}


@contextlib.contextmanager
def _sftp_connect(
    host: str,
    port: int,
    username: str,
    *,
    password: str = '',
    key_path: str = '',
    key_passphrase: str = '',
    timeout: int = 30,
):
    """Open an SFTP connection and yield the SFTPClient.

    Supports password auth and private-key auth (RSA, ECDSA, Ed25519, DSS).
    Raises ImportError if paramiko is not installed.
    Raises ValueError if neither password nor key_path is provided.
    """
    if not password and not key_path:
        raise ValueError("SFTP: either password or key_path must be configured")

    try:
        import paramiko
    except ImportError:
        raise ImportError(
            "SFTP support requires paramiko: pip install paramiko  "
            "(or pip install 'flowforge[sftp]')"
        )

    ssh = paramiko.SSHClient()
    allow_unknown = os.environ.get('FLOWFORGE_SFTP_ALLOW_UNKNOWN_HOSTS', '').lower() == 'true'
    if allow_unknown:
        # TOFU mode: trusts any host key on first connect.
        # Enable only for private networks where MITM risk is low.
        # Set FLOWFORGE_SFTP_ALLOW_UNKNOWN_HOSTS=true to opt in.
        class _TofuPolicy(paramiko.MissingHostKeyPolicy):
            def missing_host_key(self, client, hostname, key):
                client._host_keys.add(hostname, key.get_name(), key)
        ssh.set_missing_host_key_policy(_TofuPolicy())
    else:
        # Default: reject hosts not in known_hosts (secure default).
        # Add servers first: ssh-keyscan -H <host> >> ~/.ssh/known_hosts
        ssh.set_missing_host_key_policy(paramiko.RejectPolicy())

    connect_kwargs: dict[str, Any] = {
        'hostname': host,
        'port': port,
        'username': username,
        'timeout': timeout,
        'look_for_keys': False,
        'allow_agent': False,
    }
    if key_path:
        connect_kwargs['key_filename'] = [key_path]
        if key_passphrase:
            connect_kwargs['passphrase'] = key_passphrase
    else:
        connect_kwargs['password'] = password

    strict_mode = not allow_unknown
    logger.debug("SFTP: connecting to %s:%d as %s (strict_hostkeys=%s)", host, port, username, strict_mode)
    try:
        ssh.connect(**connect_kwargs)
    except paramiko.SSHException as exc:
        ssh.close()
        if strict_mode and 'not found in known_hosts' in str(exc):
            raise paramiko.SSHException(
                f"SFTP host key rejected for '{host}' (strict mode). "
                f"Add the host key with: ssh-keyscan -H {host} >> ~/.ssh/known_hosts"
                f" or set FLOWFORGE_SFTP_ALLOW_UNKNOWN_HOSTS=true to disable strict checks."
            ) from exc
        raise
    sftp = ssh.open_sftp()
    try:
        yield sftp
    finally:
        sftp.close()
        ssh.close()
        logger.debug("SFTP: connection to %s closed", host)


def _mkdir_remote(sftp, remote_dir: str) -> None:
    """Create a remote directory path recursively (equivalent to mkdir -p)."""
    prefix = '/' if remote_dir.startswith('/') else ''
    cumulative = prefix
    for segment in remote_dir.strip('/').split('/'):
        if not segment:
            continue
        cumulative = f'{cumulative}/{segment}' if cumulative and cumulative != '/' else f'/{segment}'
        try:
            sftp.stat(cumulative)
        except OSError:
            sftp.mkdir(cumulative)
            logger.debug("SFTP: created remote directory %s", cumulative)


def _remote_is_dir(sftp, path: str) -> bool:
    return stat_module.S_ISDIR(sftp.stat(path).st_mode)


class SftpTransferStep(BaseStep):
    """Download files from or upload files to a remote SFTP server.

    Config fields:
        host            SFTP server hostname or IP  (required)
        port            Port number  (default: 22)
        username        SSH username  (required)
        password        Password for auth (use this or key_path)
        key_path        Path to a private key file (RSA/ECDSA/Ed25519/DSS)
        key_passphrase  Passphrase for an encrypted private key (optional)
        timeout         Connection timeout in seconds  (default: 30)

        operation       'download' or 'upload'  (required)
        remote_path     Remote file or directory path — supports {{ variables }}
        local_path      Local file or directory path  — supports {{ variables }}

        pattern         Glob filter when remote_path is a directory (download only)
                        e.g. "*.csv", "REPORT_*.xlsx"  (default: all files)
        create_remote_dirs  Create missing remote directories before upload (default: true)
        overwrite       Overwrite existing files (default: true)
                        When false: skips files that already exist at the destination
    """

    step_type = 'sftp_transfer'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        host      = render(self.config.get('host', ''),     context).strip()
        username  = render(self.config.get('username', ''), context).strip()
        operation = render(self.config.get('operation', ''), context).strip().lower()

        if not host:
            return StepResult(success=False, error='sftp_transfer: host is required')
        if not username:
            return StepResult(success=False, error='sftp_transfer: username is required')
        if operation not in _VALID_OPERATIONS:
            return StepResult(
                success=False,
                error=f'sftp_transfer: operation must be one of: {", ".join(sorted(_VALID_OPERATIONS))}',
            )

        remote_path = render(self.config.get('remote_path', ''), context).strip()
        local_path  = render(self.config.get('local_path', ''),  context).strip()

        if not remote_path:
            return StepResult(success=False, error='sftp_transfer: remote_path is required')
        if not local_path:
            return StepResult(success=False, error='sftp_transfer: local_path is required')

        # Validate local path for uploads before opening the connection
        if operation == 'upload':
            local = Path(local_path)
            if not local.exists():
                return StepResult(success=False, error=f'Local file not found: {local_path}')
            if not local.is_file():
                return StepResult(success=False, error=f'Local path is not a file: {local_path}')

        port           = int(self.config.get('port', 22))
        password       = render(self.config.get('password', ''),       context)
        key_path       = render(self.config.get('key_path', ''),       context).strip()
        key_passphrase = render(self.config.get('key_passphrase', ''), context)
        timeout        = int(self.config.get('timeout', 30))
        pattern        = render(self.config.get('pattern', ''),        context).strip()
        overwrite      = bool(self.config.get('overwrite', True))
        create_dirs    = bool(self.config.get('create_remote_dirs', True))

        try:
            with _sftp_connect(
                host, port, username,
                password=password,
                key_path=key_path,
                key_passphrase=key_passphrase,
                timeout=timeout,
            ) as sftp:
                if operation == 'download':
                    return self._download(sftp, remote_path, local_path, pattern, overwrite)
                else:
                    return self._upload(sftp, local_path, remote_path, create_dirs, overwrite)

        except ImportError as exc:
            return StepResult(success=False, error=str(exc))
        except ValueError as exc:
            return StepResult(success=False, error=str(exc))
        except Exception as exc:
            logger.exception("SFTP transfer failed")
            return StepResult(success=False, error=f'SFTP error: {exc}')

    # ── download ───────────────────────────────────────────────────────────────

    def _download(
        self,
        sftp,
        remote_path: str,
        local_path: str,
        pattern: str,
        overwrite: bool,
    ) -> StepResult:
        try:
            is_dir = _remote_is_dir(sftp, remote_path)
        except OSError as exc:
            return StepResult(success=False, error=f'Remote path not found: {remote_path} ({exc})')

        if is_dir:
            return self._download_directory(sftp, remote_path, local_path, pattern, overwrite)
        return self._download_file(sftp, remote_path, local_path, overwrite)

    def _download_file(
        self, sftp, remote_path: str, local_path: str, overwrite: bool
    ) -> StepResult:
        local = Path(local_path)
        # If local_path is (or looks like) a directory, place the file inside it
        if local.is_dir() or local_path.endswith(('/', '\\')):
            local = local / Path(remote_path.replace('\\', '/')).name
        local.parent.mkdir(parents=True, exist_ok=True)

        if local.exists() and not overwrite:
            logger.info("SFTP download: skipping existing file %s", local)
            return StepResult(
                success=True,
                output_path=str(local),
                files_found=1,
                files_loaded=0,
                logs=f'Skipped (already exists): {local}',
            )

        sftp.get(remote_path, str(local))
        logger.info("SFTP download: %s → %s", remote_path, local)
        return StepResult(
            success=True,
            output_path=str(local),
            files_found=1,
            files_loaded=1,
            logs=f'Downloaded: {Path(remote_path).name} → {local}',
        )

    def _download_directory(
        self,
        sftp,
        remote_dir: str,
        local_dir: str,
        pattern: str,
        overwrite: bool,
    ) -> StepResult:
        entries = sftp.listdir_attr(remote_dir)
        files   = [e for e in entries if not stat_module.S_ISDIR(e.st_mode)]
        if pattern:
            files = [e for e in files if fnmatch.fnmatch(e.filename, pattern)]

        local = Path(local_dir)
        local.mkdir(parents=True, exist_ok=True)

        loaded   = 0
        failed   = 0
        skipped  = 0
        first    = ''
        errors: list[str] = []

        for entry in files:
            remote_file = f"{remote_dir.rstrip('/')}/{entry.filename}"
            local_file  = local / entry.filename

            if local_file.exists() and not overwrite:
                skipped += 1
                continue

            try:
                sftp.get(remote_file, str(local_file))
                loaded += 1
                if not first:
                    first = str(local_file)
                logger.info("SFTP download: %s → %s", entry.filename, local_file)
            except Exception as exc:
                failed += 1
                errors.append(f'{entry.filename}: {exc}')
                logger.exception("SFTP download failed for %s", entry.filename)

        log_lines = [
            f'Remote dir  : {remote_dir}',
            f'Pattern     : {pattern or "(all files)"}',
            f'Files found : {len(files)}',
            f'Downloaded  : {loaded}',
            f'Skipped     : {skipped}',
            f'Failed      : {failed}',
        ]
        if errors:
            log_lines.append('Errors:')
            log_lines.extend(f'  {e}' for e in errors)

        return StepResult(
            success=(failed == 0),
            output_path=first,
            files_found=len(files),
            files_loaded=loaded,
            files_failed=failed,
            logs='\n'.join(log_lines),
            error=f'{failed} file(s) failed to download' if failed else '',
        )

    # ── upload ─────────────────────────────────────────────────────────────────

    def _upload(
        self,
        sftp,
        local_path: str,
        remote_path: str,
        create_remote_dirs: bool,
        overwrite: bool,
    ) -> StepResult:
        local = Path(local_path)
        if not local.exists():
            return StepResult(success=False, error=f'Local file not found: {local_path}')
        if not local.is_file():
            return StepResult(success=False, error=f'Local path is not a file: {local_path}')

        # If remote_path ends with / or \, append the local filename
        if remote_path.endswith(('/', '\\')):
            remote_file = remote_path.rstrip('/\\') + '/' + local.name
        else:
            remote_file = remote_path

        # Create remote directory tree if needed
        remote_dir = remote_file.rsplit('/', 1)[0]
        if remote_dir and create_remote_dirs:
            try:
                _mkdir_remote(sftp, remote_dir)
            except Exception as exc:
                return StepResult(
                    success=False,
                    error=f'Failed to create remote directory {remote_dir}: {exc}',
                )

        # Skip if remote file already exists and overwrite=false
        if not overwrite:
            try:
                sftp.stat(remote_file)
                logger.info("SFTP upload: skipping existing remote file %s", remote_file)
                return StepResult(
                    success=True,
                    files_loaded=0,
                    logs=f'Skipped (already exists on remote): {remote_file}',
                )
            except OSError:
                pass  # doesn't exist — proceed with upload

        sftp.put(str(local), remote_file)
        logger.info("SFTP upload: %s → %s", local.name, remote_file)
        return StepResult(
            success=True,
            files_loaded=1,
            logs=f'Uploaded: {local.name} → {remote_file}  ({local.stat().st_size:,} bytes)',
        )
