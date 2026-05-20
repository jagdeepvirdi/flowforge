"""Append-only audit log — written to logs/audit.log.

Records login attempts and pipeline run outcomes. Runs outside the Flask
request context (background threads) so it uses a plain file handler rather
than the Flask logger.
"""
import logging
import os
from pathlib import Path

_LOG_DIR = Path(os.environ.get('FLOWFORGE_LOG_DIR', 'logs'))
_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger('flowforge.audit')
        if not logger.handlers:
            handler = logging.FileHandler(_LOG_DIR / 'audit.log')
            handler.setFormatter(
                logging.Formatter('%(asctime)sZ  %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
            )
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        _logger = logger
    return _logger


def log_login(username: str, success: bool, remote_addr: str = '') -> None:
    outcome = 'SUCCESS' if success else 'FAILED'
    _get_logger().info('LOGIN     %-7s  user=%-20s  ip=%s', outcome, username, remote_addr or 'unknown')


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
