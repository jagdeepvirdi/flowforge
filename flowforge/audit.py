"""Append-only audit log.

Writes to logs/audit.log (rotating) by default.  When FLOWFORGE_AUDIT_STDOUT=true
is set, structured JSON lines are also written to stdout so container log
aggregators (Fluentd, Loki, CloudWatch) can capture the audit trail without a
mounted volume.  The file handler is still active unless FLOWFORGE_AUDIT_FILE=false
is set.

Rotation: 10 MB per file, 5 backups (logs/audit.log → audit.log.1 … .5).
Log level: always INFO regardless of LOG_LEVEL — the audit log is a security
record and must not be silenced by production log-level configuration.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(os.environ.get('FLOWFORGE_LOG_DIR', 'logs'))
_logger: logging.Logger | None = None

_AUDIT_STDOUT = os.environ.get('FLOWFORGE_AUDIT_STDOUT', '').lower() == 'true'
_AUDIT_FILE   = os.environ.get('FLOWFORGE_AUDIT_FILE',   'true').lower() != 'false'


class _JsonStdoutHandler(logging.Handler):
    """Emit audit records as JSON lines to stdout."""

    def emit(self, record: logging.LogRecord) -> None:
        payload = {
            'ts':      datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'level':   record.levelname,
            'logger':  record.name,
            'message': record.getMessage(),
        }
        try:
            sys.stdout.write(json.dumps(payload) + '\n')
            sys.stdout.flush()
        except Exception:
            pass


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        logger = logging.getLogger('flowforge.audit')
        if not logger.handlers:
            if _AUDIT_FILE:
                _LOG_DIR.mkdir(parents=True, exist_ok=True)
                file_handler = RotatingFileHandler(
                    _LOG_DIR / 'audit.log',
                    maxBytes=10 * 1024 * 1024,
                    backupCount=5,
                    encoding='utf-8',
                )
                file_handler.setFormatter(
                    logging.Formatter('%(asctime)sZ  %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
                )
                logger.addHandler(file_handler)
            if _AUDIT_STDOUT:
                logger.addHandler(_JsonStdoutHandler())
        logger.setLevel(logging.INFO)  # hardcoded — audit log must not follow LOG_LEVEL
        logger.propagate = False
        _logger = logger
    return _logger


def log_login(username: str, success: bool, remote_addr: str = '') -> None:
    outcome = 'SUCCESS' if success else 'FAILED'
    _get_logger().info('LOGIN     %-7s  user=%-20s  ip=%s', outcome, username, remote_addr or 'unknown')


def log_logout(username: str, remote_addr: str = '') -> None:
    _get_logger().info('LOGOUT             user=%-20s  ip=%s', username, remote_addr or 'unknown')


def log_pipeline_run(
    pipeline_name: str,
    triggered_by: str,
    run_id: str,
    status: str,
) -> None:
    _get_logger().info(
        'PIPELINE  %-8s  pipeline=%-30r  triggered_by=%-10s  run_id=%s',
        status.upper(), pipeline_name, triggered_by, run_id,
    )


def log_connection_change(action: str, name: str, conn_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('CONNECTION %-7s  name=%-30r  id=%s', action.upper(), name, conn_id)


def log_provider_change(action: str, name: str, provider_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('PROVIDER   %-7s  name=%-30r  id=%s', action.upper(), name, provider_id)


def log_email_sent(
    pipeline_name: str,
    step_name: str,
    subject: str,
    recipients: list[str],
    attachment_names: list[str],
) -> None:
    attachments = ', '.join(attachment_names) if attachment_names else 'none'
    _get_logger().info(
        'EMAIL_SENT  pipeline=%-20r  step=%-20r  subject=%-40r  recipients=%d  attachments=%s',
        pipeline_name, step_name, subject, len(recipients), attachments,
    )


def log_webhook_trigger(pipeline_name: str, run_id: str, remote_addr: str = '') -> None:
    _get_logger().info(
        'WEBHOOK_TRIGGER  pipeline=%-30r  run_id=%s  ip=%s',
        pipeline_name, run_id, remote_addr or 'unknown',
    )


def log_report_exported(
    pipeline_name: str,
    step_name: str,
    output_filename: str,
    row_count: int,
    fmt: str,
) -> None:
    _get_logger().info(
        'REPORT_EXPORTED  pipeline=%-20r  step=%-20r  file=%-40s  rows=%d  format=%s',
        pipeline_name, step_name, output_filename, row_count, fmt,
    )
