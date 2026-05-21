"""APScheduler integration — loads enabled pipelines and registers cron jobs."""
import logging
import os

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)

# Stored at module level so job functions (which run in worker threads) can
# create their own app contexts without receiving the app as a pickled arg.
_app = None


def start_scheduler(app) -> None:
    """Start the blocking APScheduler daemon.

    Must be called with the Flask app object directly — NOT from inside an
    existing app context. Each scheduled job creates its own short-lived
    app context so that Flask-SQLAlchemy sessions are properly scoped per run.
    """
    global _app
    _app = app

    db_url = os.environ.get('FLOWFORGE_DB_URL', '')
    jobstores = {'default': SQLAlchemyJobStore(url=db_url)} if db_url else {}

    scheduler = BlockingScheduler(jobstores=jobstores, timezone='UTC')

    # Load pipeline jobs inside a temporary app context, then release it.
    # The scheduler itself holds no DB connection between job runs.
    with app.app_context():
        _load_pipeline_jobs(scheduler)

    _register_cleanup_job(scheduler)

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


def _load_pipeline_jobs(scheduler: BlockingScheduler) -> None:
    """Register one cron job per enabled scheduled pipeline. Must be called
    inside an active app context."""
    from flowforge.db.models import Pipeline, db

    pipelines = db.session.query(Pipeline).filter_by(enabled=True).all()
    registered = 0
    for pipeline in pipelines:
        if not pipeline.schedule:
            continue
        try:
            cron_parts = pipeline.schedule.strip().split()
            if len(cron_parts) != 5:
                logger.warning("Invalid cron expression for '%s': %s", pipeline.name, pipeline.schedule)
                continue
            minute, hour, day, month, day_of_week = cron_parts
            scheduler.add_job(
                _run_pipeline_job,
                trigger='cron',
                # pipeline_id and pipeline_name are plain strings — safe to pickle
                args=[pipeline.id, pipeline.name],
                id=f'pipeline_{pipeline.id}',
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                replace_existing=True,
                misfire_grace_time=300,
            )
            registered += 1
            logger.info("Scheduled '%s': %s", pipeline.name, pipeline.schedule)
        except Exception as e:
            logger.error("Failed to register schedule for '%s': %s", pipeline.name, e)

    logger.info("Registered %d scheduled pipeline(s).", registered)


def _register_cleanup_job(scheduler: BlockingScheduler) -> None:
    scheduler.add_job(
        _cleanup_job,
        trigger='cron',
        hour=2, minute=0,
        id='output_cleanup',
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Registered daily output cleanup job (02:00 UTC).")


def _cleanup_job() -> None:
    from flowforge.engine.cleanup import cleanup_output_files
    cleanup_output_files()


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
