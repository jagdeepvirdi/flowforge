"""APScheduler integration — loads enabled pipelines and registers cron jobs."""
import logging
import os

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

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        _scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


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
        except Exception as e:
            logger.error("Failed to register schedule for '%s': %s", pipeline.name, e)

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
    cleanup_output_files()
    _prune_token_blocklist()


def _prune_token_blocklist() -> None:
    if _app is None:
        return
    try:
        from datetime import datetime, timezone
        with _app.app_context():
            from flowforge.db.models import TokenBlocklist, db
            deleted = (
                db.session.query(TokenBlocklist)
                .filter(TokenBlocklist.expires_at < datetime.now(timezone.utc))
                .delete()
            )
            db.session.commit()
            if deleted:
                logger.info("Pruned %d expired token blocklist entry/entries.", deleted)
    except Exception as e:
        logger.error("Token blocklist pruning failed: %s", e)


def _sync_db_job() -> None:
    """Periodic job: reconcile APScheduler state with current pipeline DB state."""
    if _app is None:
        return
    try:
        with _app.app_context():
            _sync_pipeline_jobs()
    except Exception as e:
        logger.error("Pipeline sync failed: %s", e)


def _run_pipeline_job(pipeline_id: str, pipeline_name: str) -> None:
    """Entry point called by APScheduler worker threads.

    Creates its own Flask app context so Flask-SQLAlchemy and other
    context-locals are properly initialised for this thread.
    """
    if _app is None:
        logger.error("Scheduler app not initialised — cannot run '%s'", pipeline_name)
        return

    from flowforge.engine.loader import load_pipeline
    from flowforge.engine.runner import run_pipeline

    try:
        with _app.app_context():
            steps, pipeline_vars, secret_keys = load_pipeline(pipeline_id)
            run_pipeline(
                pipeline_name=pipeline_name,
                steps=steps,
                pipeline_vars=pipeline_vars,
                triggered_by='scheduler',
                pipeline_id=pipeline_id,
                secret_var_keys=secret_keys,
            )
    except Exception as e:
        logger.error("Scheduled run of '%s' failed: %s", pipeline_name, e)
