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
from datetime import UTC, datetime
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
            'ts':      datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
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

def _current_user() -> str:
    try:
        from flask import g
        return g.user_token.get('sub', 'system')
    except (RuntimeError, AttributeError):
        return 'system'

def _current_user_id() -> str:
    try:
        from flask import g
        return getattr(g, 'current_user_id', 'system')
    except (RuntimeError, AttributeError):
        return 'system'

def _write_db_audit(action: str, username: str, user_id: str, ip_address: str, details: dict) -> None:
    try:
        from flask import current_app
        if not current_app:
            return
        from sqlalchemy import insert

        from flowforge.db.models import AuditLog, db
        
        stmt = insert(AuditLog).values(
            action=action,
            username=username,
            user_id=user_id if user_id != 'system' else None,
            ip_address=ip_address,
            details=details
        )
        with db.engine.begin() as conn:
            conn.execute(stmt)
    except Exception:
        pass


def log_login(username: str, success: bool, remote_addr: str = '') -> None:
    outcome = 'SUCCESS' if success else 'FAILED'
    # Logins might not have a g.current_user_id if failed, but we can look it up or leave it 'unknown'
    _get_logger().info('LOGIN     %-7s  user=%-20s  ip=%s  user_id=%s', outcome, username, remote_addr or 'unknown', _current_user_id())
    _write_db_audit(f'LOGIN_{outcome}', username, _current_user_id(), remote_addr, {})


def log_logout(username: str, remote_addr: str = '') -> None:
    _get_logger().info('LOGOUT             user=%-20s  ip=%s  user_id=%s', username, remote_addr or 'unknown', _current_user_id())
    _write_db_audit('LOGOUT', username, _current_user_id(), remote_addr, {})


def log_pipeline_run(
    pipeline_name: str,
    triggered_by: str,
    run_id: str,
    status: str,
) -> None:
    _get_logger().info(
        'PIPELINE  %-8s  pipeline=%-30r  triggered_by=%-10s  run_id=%s  by=%s  user_id=%s',
        status.upper(), pipeline_name, triggered_by, run_id, _current_user(), _current_user_id()
    )
    _write_db_audit(f'PIPELINE_{status.upper()}', _current_user(), _current_user_id(), '', {
        'pipeline_name': pipeline_name,
        'triggered_by': triggered_by,
        'run_id': run_id,
    })


def log_connection_change(action: str, name: str, conn_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('CONNECTION %-7s  name=%-30r  id=%s  by=%s  user_id=%s', action.upper(), name, conn_id, _current_user(), _current_user_id())
    _write_db_audit(f'CONNECTION_{action.upper()}', _current_user(), _current_user_id(), '', {'name': name, 'id': conn_id})


def log_provider_change(action: str, name: str, provider_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('PROVIDER   %-7s  name=%-30r  id=%s  by=%s  user_id=%s', action.upper(), name, provider_id, _current_user(), _current_user_id())
    _write_db_audit(f'PROVIDER_{action.upper()}', _current_user(), _current_user_id(), '', {'name': name, 'id': provider_id})


def log_pipeline_change(action: str, name: str, pipeline_id: str) -> None:
    """action: CREATED | UPDATED | DELETED | CLONED | IMPORTED"""
    _get_logger().info('PIPELINE_CFG %-7s name=%-30r  id=%s  by=%s  user_id=%s', action.upper(), name, pipeline_id, _current_user(), _current_user_id())
    _write_db_audit(f'PIPELINE_CFG_{action.upper()}', _current_user(), _current_user_id(), '', {'name': name, 'id': pipeline_id})


def log_report_change(action: str, name: str, report_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('REPORT_CFG   %-7s name=%-30r  id=%s  by=%s  user_id=%s', action.upper(), name, report_id, _current_user(), _current_user_id())
    _write_db_audit(f'REPORT_CFG_{action.upper()}', _current_user(), _current_user_id(), '', {'name': name, 'id': report_id})


def log_bulk_load_change(action: str, name: str, config_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('BULKLOAD_CFG %-7s name=%-30r  id=%s  by=%s  user_id=%s', action.upper(), name, config_id, _current_user(), _current_user_id())
    _write_db_audit(f'BULKLOAD_CFG_{action.upper()}', _current_user(), _current_user_id(), '', {'name': name, 'id': config_id})


def log_recipient_change(action: str, name: str, group_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('RECIPIENTS   %-7s name=%-30r  id=%s  by=%s  user_id=%s', action.upper(), name, group_id, _current_user(), _current_user_id())
    _write_db_audit(f'RECIPIENTS_{action.upper()}', _current_user(), _current_user_id(), '', {'name': name, 'id': group_id})


def log_project_change(action: str, name: str, project_id: str) -> None:
    """action: CREATED | UPDATED | DELETED"""
    _get_logger().info('PROJECT      %-7s name=%-30r  id=%s  by=%s  user_id=%s', action.upper(), name, project_id, _current_user(), _current_user_id())
    _write_db_audit(f'PROJECT_{action.upper()}', _current_user(), _current_user_id(), '', {'name': name, 'id': project_id})


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
    _write_db_audit('EMAIL_SENT', _current_user(), _current_user_id(), '', {
        'pipeline_name': pipeline_name,
        'step_name': step_name,
        'subject': subject,
        'recipients_count': len(recipients),
        'attachments': attachments,
    })


def log_webhook_trigger(pipeline_name: str, run_id: str, remote_addr: str = '') -> None:
    _get_logger().info(
        'WEBHOOK_TRIGGER  pipeline=%-30r  run_id=%s  ip=%s',
        pipeline_name, run_id, remote_addr or 'unknown',
    )
    _write_db_audit('WEBHOOK_TRIGGER', _current_user(), _current_user_id(), remote_addr, {
        'pipeline_name': pipeline_name,
        'run_id': run_id,
    })


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
    _write_db_audit('REPORT_EXPORTED', _current_user(), _current_user_id(), '', {
        'pipeline_name': pipeline_name,
        'step_name': step_name,
        'output_filename': output_filename,
        'row_count': row_count,
        'format': fmt,
    })

