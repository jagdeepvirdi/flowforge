"""APScheduler integration — loads enabled pipelines and registers cron jobs."""
import logging
import os
from datetime import UTC

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)

# Stored at module level so job functions (which run in worker threads) can
# create their own app contexts without receiving the app as a pickled arg.
_app = None
_scheduler = None


def start_scheduler(app) -> None:
    """Start the blocking APScheduler daemon.

    Must be called with the Flask app object directly — NOT from inside an
    existing app context. Each scheduled job creates its own short-lived
    app context so that Flask-SQLAlchemy sessions are properly scoped per run.
    """
    global _app, _scheduler
    _app = app

    db_url = os.environ.get('FLOWFORGE_DB_URL', '')
    if db_url:
        jobstores = {'default': SQLAlchemyJobStore(url=db_url)}
        # Log host/db portion only — never log credentials
        _safe_url = db_url.split('@')[-1] if '@' in db_url else db_url
        logger.info("Jobstore: PostgreSQL (%s) — jobs survive scheduler restarts.", _safe_url)
    else:
        jobstores = {}
        logger.warning(
            "FLOWFORGE_DB_URL is not set — using in-memory jobstore. "
            "All scheduled jobs will be lost on scheduler restart."
        )

    _scheduler = BlockingScheduler(jobstores=jobstores, timezone='UTC')

    with app.app_context():
        _sync_pipeline_jobs()

    _register_cleanup_job()
    _register_sync_job()
    _register_audit_verify_job()

    from flowforge.engine import leader

    def _run() -> None:
        logger.info("Scheduler started. Press Ctrl+C to stop.")
        try:
            _scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")

    if leader.ha_enabled():
        logger.info(
            "HA: FLOWFORGE_REDIS_URL is set — using distributed leader election so only one "
            "scheduler replica fires jobs at a time."
        )
        leader.run_with_leadership(_run)
    else:
        logger.warning(
            "HA: FLOWFORGE_REDIS_URL is not set — no leader election is possible. Do not run "
            "more than one scheduler replica, or the same cron job will fire once per replica."
        )
        _run()


def _sync_pipeline_jobs() -> None:
    """Reconcile APScheduler jobs with current DB state.

    Adds new jobs, updates changed schedules, and removes jobs for pipelines
    that have had their schedule cleared or been disabled. Must be called
    inside an active app context.
    """
    from flowforge.db.models import Pipeline, db

    existing_ids = {j.id for j in _scheduler.get_jobs() if j.id.startswith('pipeline_')}

    pipelines = db.session.query(Pipeline).filter_by(enabled=True).all()
    active_ids = set()
    registered = 0

    for pipeline in pipelines:
        if not pipeline.schedule:
            continue
        job_id = f'pipeline_{pipeline.id}'
        try:
            cron_parts = pipeline.schedule.strip().split()
            if len(cron_parts) != 5:
                logger.warning("Invalid cron expression for '%s': %s", pipeline.name, pipeline.schedule)
                continue
            minute, hour, day, month, day_of_week = cron_parts
            _scheduler.add_job(
                _run_pipeline_job,
                trigger='cron',
                args=[pipeline.id, pipeline.name],
                id=job_id,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                replace_existing=True,
                misfire_grace_time=300,
            )
            active_ids.add(job_id)
            registered += 1
            logger.info("Scheduled '%s': %s", pipeline.name, pipeline.schedule)
        except Exception:
            logger.exception("Failed to register schedule for '%s'", pipeline.name)

    # Remove jobs whose pipeline has been disabled or schedule cleared
    for stale_id in existing_ids - active_ids:
        _scheduler.remove_job(stale_id)
        logger.info("Removed stale job: %s", stale_id)

    removed = len(existing_ids - active_ids)
    logger.info("Sync complete: %d active job(s), %d removed.", registered, removed)


def _register_cleanup_job() -> None:
    _scheduler.add_job(
        _cleanup_job,
        trigger='cron',
        hour=2, minute=0,
        id='output_cleanup',
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Registered daily output cleanup job (02:00 UTC).")


DEFAULT_AUDIT_VERIFY_CRON = '0 3 * * *'      # after the 02:00 retention prune, so it checks the pruned log
_AUDIT_VERIFY_JOB_ID = 'audit_chain_verify'


def _audit_verify_trigger():
    """CronTrigger from FLOWFORGE_AUDIT_VERIFY_CRON; ``None`` only when explicitly turned off.

    A bad expression falls back to the default (with an error), never to "disabled": a typo must not
    quietly switch off the integrity check.
    """
    from apscheduler.triggers.cron import CronTrigger
    raw = os.environ.get('FLOWFORGE_AUDIT_VERIFY_CRON', '').strip()
    if raw.lower() in ('off', 'false', 'disabled', 'none'):
        return None
    try:
        return CronTrigger.from_crontab(raw or DEFAULT_AUDIT_VERIFY_CRON, timezone='UTC')
    except ValueError as e:
        logger.error("FLOWFORGE_AUDIT_VERIFY_CRON=%r is not a valid 5-field cron expression (%s); "
                     "using the default %r", raw, e, DEFAULT_AUDIT_VERIFY_CRON)
        return CronTrigger.from_crontab(DEFAULT_AUDIT_VERIFY_CRON, timezone='UTC')


def _register_audit_verify_job() -> None:
    from apscheduler.jobstores.base import JobLookupError
    trigger = _audit_verify_trigger()
    if trigger is None:
        try:
            _scheduler.remove_job(_AUDIT_VERIFY_JOB_ID)        # it may persist in the job store from an earlier run
        except JobLookupError:
            pass
        logger.warning("Audit chain verification is DISABLED (FLOWFORGE_AUDIT_VERIFY_CRON=off): tampering "
                       "with the audit log will not be detected until `flowforge audit verify` is run by hand.")
        return
    _scheduler.add_job(
        _verify_audit_chain_job,
        trigger=trigger,
        id=_AUDIT_VERIFY_JOB_ID,
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )
    logger.info("Registered audit chain verification job (%s).", trigger)


def _verify_audit_chain_job() -> None:
    """Recompute the audit hash chain and alert if it does not pass (see flowforge/audit_chain.py)."""
    if _app is None:
        return
    try:
        from flowforge import audit, audit_chain
        with _app.app_context():
            from flowforge.db.models import db
            try:
                with db.engine.connect() as conn:
                    report = audit_chain.verify(conn)
            except Exception as e:
                logger.exception("Audit chain verification could not run")
                audit.log_chain_verification(error=f'{type(e).__name__}: {str(e)[:200]}')
                return
            audit.log_chain_verification(report)
    except Exception:
        logger.exception("Audit chain verification job failed")


def _register_sync_job() -> None:
    _scheduler.add_job(
        _sync_db_job,
        trigger='interval',
        minutes=1,
        id='_pipeline_sync',
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("Registered pipeline sync job (every 60s).")


def _cleanup_job() -> None:
    from flowforge.engine.cleanup import cleanup_output_files
    # Wrapped in an app context (when available) so cleanup_output_files() can
    # resolve a DB-backed FLOWFORGE_OUTPUT_TTL_DAYS override, same as the prune
    # functions below do for their own retention settings.
    if _app is not None:
        with _app.app_context():
            cleanup_output_files()
    else:
        cleanup_output_files()
    _prune_token_blocklist()
    _prune_expired_password_reset_tokens()
    _prune_old_runs()
    _prune_old_audit_logs()
    _prune_old_token_map()


def _prune_old_runs() -> None:
    if _app is None:
        return
    try:
        from datetime import datetime, timedelta

        from flowforge.engine.settings import get_run_retention_days
        with _app.app_context():
            retention_days = get_run_retention_days()
            if retention_days <= 0:
                return
            from flowforge.db.models import PipelineRun, db
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            # Delete runs older than cutoff. Cascading takes care of step_runs.
            deleted = (
                db.session.query(PipelineRun)
                .filter(PipelineRun.started_at < cutoff)
                .delete(synchronize_session=False)
            )
            db.session.commit()
            if deleted:
                logger.info("Pruned %d pipeline run(s) older than %d days.", deleted, retention_days)
    except Exception:
        logger.exception("Pipeline run pruning failed")


def _prune_old_audit_logs() -> None:
    if _app is None:
        return
    try:
        from datetime import datetime, timedelta

        from flowforge.engine.settings import get_audit_retention_days
        with _app.app_context():
            retention_days = get_audit_retention_days()
            if retention_days <= 0:
                return
            from flowforge import audit_chain
            from flowforge.db.models import db
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            try:
                # leaves a chained AUDIT_PRUNED checkpoint so the log stays verifiable (audit_chain.py)
                deleted = audit_chain.prune(db.session.connection(), cutoff)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            if deleted:
                logger.info("Pruned %d audit log(s) older than %d days.", deleted, retention_days)
    except Exception:
        logger.exception("Audit log pruning failed")


def _prune_old_token_map() -> None:
    """Delete token -> subscriber mappings not seen within FLOWFORGE_TOKEN_MAP_RETENTION_DAYS."""
    if _app is None:
        return
    try:
        from flowforge import token_store
        with _app.app_context():
            days = token_store.retention_days()
            if days <= 0:
                return
            deleted = token_store.purge(days)
            if deleted:
                logger.info("Pruned %d token mapping(s) not seen for %d days.", deleted, days)
    except Exception:
        logger.exception("Token map pruning failed")


def _prune_token_blocklist() -> None:
    if _app is None:
        return
    try:
        from datetime import datetime
        with _app.app_context():
            from flowforge.db.models import TokenBlocklist, db
            deleted = (
                db.session.query(TokenBlocklist)
                .filter(TokenBlocklist.expires_at < datetime.now(UTC))
                .delete()
            )
            db.session.commit()
            if deleted:
                logger.info("Pruned %d expired token blocklist entry/entries.", deleted)
    except Exception:
        logger.exception("Token blocklist pruning failed")


def _prune_expired_password_reset_tokens() -> None:
    """Single-use tokens are never deleted on use or expiry by the reset flow itself
    (it only checks expires_at/used_at) — sweep them here so the table doesn't grow forever."""
    if _app is None:
        return
    try:
        from datetime import datetime
        with _app.app_context():
            from flowforge.db.models import PasswordResetToken, db
            deleted = (
                db.session.query(PasswordResetToken)
                .filter(PasswordResetToken.expires_at < datetime.now(UTC))
                .delete()
            )
            db.session.commit()
            if deleted:
                logger.info("Pruned %d expired password reset token(s).", deleted)
    except Exception:
        logger.exception("Password reset token pruning failed")


def _sync_db_job() -> None:
    """Periodic job: reconcile APScheduler state with current pipeline DB state."""
    if _app is None:
        return
    try:
        with _app.app_context():
            _sync_pipeline_jobs()
    except Exception:
        logger.exception("Pipeline sync failed")


def _run_pipeline_job(pipeline_id: str, pipeline_name: str) -> None:
    """Entry point called by APScheduler worker threads.

    Creates its own Flask app context so Flask-SQLAlchemy and other
    context-locals are properly initialised for this thread.
    """
    if _app is None:
        logger.error("Scheduler app not initialised — cannot run '%s'", pipeline_name)
        return

    from flowforge.db.models import Pipeline, db
    from flowforge.engine.launcher import launch_run

    try:
        with _app.app_context():
            pipeline = db.session.get(Pipeline, pipeline_id)
            if not pipeline:
                logger.error("Pipeline %s not found for scheduled run", pipeline_id)
                return

            res, status = launch_run(pipeline, triggered_by='scheduler', app=_app)
            if status != 202:
                logger.warning("Scheduled launch of '%s' deferred: %s", pipeline_name, res.get('error'))
    except Exception:
        logger.exception("Scheduled run of '%s' failed", pipeline_name)
