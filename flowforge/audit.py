"""Append-only audit log — written to logs/audit.log.

Records login attempts and pipeline run outcomes. Runs outside the Flask
request context (background threads) so it uses a plain file handler rather
than the Flask logger.

Rotation: 10 MB per file, 5 backups (logs/audit.log → audit.log.1 … .5).
Log level: always INFO regardless of LOG_LEVEL — the audit log is a security
record and must not be silenced by production log-level configuration.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(os.environ.get('FLOWFORGE_LOG_DIR', 'logs'))
_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger('flowforge.audit')
        if not logger.handlers:
            handler = RotatingFileHandler(
                _LOG_DIR / 'audit.log',
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8',
            )
            handler.setFormatter(
                logging.Formatter('%(asctime)sZ  %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
            )
            logger.addHandler(handler)
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
