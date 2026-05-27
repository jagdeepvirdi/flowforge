"""Graceful-shutdown coordination for in-flight pipeline runs.

When SIGTERM is received (systemd stop / Docker stop):
  1. A shutdown event is set so callers can check is_shutdown_requested().
  2. The handler waits up to FLOWFORGE_SHUTDOWN_TIMEOUT seconds for active
     runs to finish naturally.
  3. Any run still marked 'running' in the DB is updated to 'cancelled'.
  4. SystemExit(0) is raised so the process exits cleanly.

Usage:
    # In cli.py, before starting the blocking event loop:
    shutdown.install_handler(app)

    # In runner.py, bracket each pipeline execution:
    shutdown.register_run(run_id)
    try:
        ...
    finally:
        shutdown.unregister_run(run_id)

    # After the event loop exits (Ctrl+C / normal stop):
    shutdown.graceful_exit(app)
"""
import atexit
import logging
import os
import signal
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GRACEFUL_TIMEOUT_SECS = int(os.environ.get('FLOWFORGE_SHUTDOWN_TIMEOUT', '60'))

_shutdown_event = threading.Event()
_active_runs: set[str] = set()
_lock = threading.Lock()
_app = None  # set by install_handler; used by _cancel_stuck_runs via atexit


# ── public API ────────────────────────────────────────────────────────────────

def register_run(run_id: str) -> None:
    with _lock:
        _active_runs.add(run_id)


def unregister_run(run_id: str) -> None:
    with _lock:
        _active_runs.discard(run_id)


def is_shutdown_requested() -> bool:
    return _shutdown_event.is_set()


def install_handler(app) -> None:
    """Install a SIGTERM handler for graceful shutdown.

    Must be called from the main thread before starting any background workers.
    Also registers an atexit hook so stuck runs are cancelled even on unexpected
    exits (e.g. unhandled exception in main thread).
    """
    global _app
    _app = app
    atexit.register(_cancel_stuck_runs)

    def _sigterm_handler(signum, frame):
        with _lock:
            inflight = len(_active_runs)
        logger.info(
            'SIGTERM received — draining %d in-flight run(s) (timeout=%ds).',
            inflight, GRACEFUL_TIMEOUT_SECS,
        )
        clean = _drain(GRACEFUL_TIMEOUT_SECS)
        if not clean:
            logger.warning('Shutdown timeout exceeded — cancelling stuck runs.')
            _cancel_stuck_runs()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _sigterm_handler)
    logger.debug('Graceful shutdown handler installed (timeout=%ds).', GRACEFUL_TIMEOUT_SECS)


def graceful_exit(app, timeout: int = GRACEFUL_TIMEOUT_SECS) -> None:
    """Call after the main event loop exits (Ctrl+C or SIGTERM absorbed by a framework).

    Sets the shutdown event, waits for active runs to drain, then cancels any
    that are still marked 'running' in the DB. Safe to call even if the SIGTERM
    handler already ran (the drain is instant when no runs are active).
    """
    global _app
    _app = app
    _shutdown_event.set()
    with _lock:
        inflight = len(_active_runs)
    if inflight:
        logger.info('Draining %d in-flight run(s) (timeout=%ds)...', inflight, timeout)
    clean = _drain(timeout)
    if not clean:
        logger.warning('Drain timeout exceeded — cancelling stuck runs.')
        _cancel_stuck_runs()
    else:
        logger.info('Graceful exit: all runs finished cleanly.')


# ── internals ─────────────────────────────────────────────────────────────────

def _drain(timeout: int) -> bool:
    """Poll until active_runs is empty or timeout expires. Returns True if clean."""
    _shutdown_event.set()
    elapsed = 0.0
    while elapsed < timeout:
        with _lock:
            if not _active_runs:
                return True
        time.sleep(0.5)
        elapsed += 0.5
    with _lock:
        return not _active_runs


def _cancel_stuck_runs() -> None:
    """Mark every status='running' row in the DB as 'cancelled'.

    Called by the atexit hook and by the SIGTERM handler on timeout.
    Safe to call multiple times — a second pass finds nothing to cancel.
    """
    if _app is None:
        return
    try:
        with _app.app_context():
            from sqlalchemy.exc import SQLAlchemyError

            from flowforge.db.models import PipelineRun, db
            try:
                stuck = db.session.query(PipelineRun).filter_by(status='running').all()
                if not stuck:
                    return
                now = datetime.now(timezone.utc)
                for run in stuck:
                    run.status = 'cancelled'
                    run.finished_at = now
                    if run.started_at:
                        run.duration_ms = int(
                            (now - run.started_at).total_seconds() * 1000
                        )
                    run.error_message = 'Process shutdown before run completed'
                db.session.commit()
                logger.warning('Marked %d stuck run(s) as cancelled.', len(stuck))
            except SQLAlchemyError:
                logger.exception('Failed to cancel stuck runs')
    except Exception:
        logger.exception('Shutdown cleanup error')
