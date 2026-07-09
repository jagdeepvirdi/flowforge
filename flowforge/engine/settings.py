"""Resolves instance-wide operational settings.

Each getter checks the `ff_system_settings` singleton row first; if the
relevant column is unset (or the row/DB is unreachable), it falls back to
the same env-var logic these values have always used. Callers that already
have a DB connection available (i.e. are inside an active Flask app
context) get the DB override transparently; callers with no app context
(e.g. a bare script) just get the env-var behavior, unchanged.
"""
import logging
import os

logger = logging.getLogger(__name__)


def _singleton_row():
    """Fetch the ff_system_settings row (id=1), or None if unset/unreachable.

    Safe to call with or without an active Flask app context — falls back
    to None (i.e. "no override") rather than raising.
    """
    try:
        from flowforge.db.models import SystemSettings, db
        return db.session.get(SystemSettings, 1)
    except Exception:
        logger.debug("Could not read ff_system_settings; using env var defaults", exc_info=True)
        return None


def get_run_retention_days() -> int:
    row = _singleton_row()
    if row is not None and row.run_retention_days is not None:
        return row.run_retention_days
    return int(os.environ.get('FLOWFORGE_RUN_RETENTION_DAYS', 90))


def get_audit_retention_days() -> int:
    row = _singleton_row()
    if row is not None and row.audit_retention_days is not None:
        return row.audit_retention_days
    return int(os.environ.get('FLOWFORGE_AUDIT_RETENTION_DAYS', os.environ.get('FLOWFORGE_RUN_RETENTION_DAYS', 90)))


def get_output_ttl_days() -> int:
    row = _singleton_row()
    if row is not None and row.output_ttl_days is not None:
        return row.output_ttl_days
    from flowforge.engine.cleanup import _DEFAULT_TTL_DAYS
    return int(os.environ.get('FLOWFORGE_OUTPUT_TTL_DAYS', _DEFAULT_TTL_DAYS))
