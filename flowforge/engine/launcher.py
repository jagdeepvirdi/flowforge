import logging
import os
import threading
from datetime import UTC
from typing import Any

from flowforge.db.models import Pipeline, PipelineRun, db
from flowforge.engine import concurrency

logger = logging.getLogger(__name__)


def launch_run(pipeline: Pipeline, triggered_by: str, app: Any = None) -> tuple[dict, int]:
    """Create a PipelineRun record and dispatch the pipeline for async execution.

    When FLOWFORGE_REDIS_URL is set the run is dispatched as a Celery task;
    otherwise it falls back to a background daemon thread. Either way, a
    FLOWFORGE_MAX_CONCURRENT_RUNS slot (see flowforge.engine.concurrency) is
    reserved before dispatch and released when the pipeline finishes.

    Returns (json_dict, status_code) immediately.
    """
    if not pipeline.enabled:
        return {'error': 'Pipeline is disabled'}, 400

    token = concurrency.try_acquire()
    if token is None:
        return {'error': 'Too many concurrent pipeline runs. Try again later.'}, 429

    run = PipelineRun(
        pipeline_id=pipeline.id,
        pipeline_name=pipeline.name,
        status='running',
        triggered_by=triggered_by,
    )
    db.session.add(run)
    db.session.commit()
    run_id = run.id

    if _use_celery():
        from flowforge.tasks import run_pipeline_task
        run_pipeline_task.delay(pipeline.id, triggered_by, run_id, token)
        logger.debug("Dispatched pipeline '%s' (run %s) to Celery.", pipeline.name, run_id)
    else:
        flask_app = app or _current_app()
        t = threading.Thread(
            target=_run_in_thread,
            args=(flask_app, pipeline.id, pipeline.name, triggered_by, run_id, token),
            daemon=True,
        )
        t.start()
        logger.debug("Dispatched pipeline '%s' (run %s) in thread.", pipeline.name, run_id)

    return {'run_id': run_id, 'status': 'running', 'pipeline_name': pipeline.name}, 202


def _use_celery() -> bool:
    """Return True when a Redis broker URL is configured."""
    return bool(os.environ.get('FLOWFORGE_REDIS_URL', ''))


def _current_app():
    from flask import current_app
    return current_app._get_current_object()


def _run_in_thread(app, pipeline_id: str, pipeline_name: str, triggered_by: str, run_id: str, token: str | None = None):
    from flowforge.engine.loader import load_pipeline
    from flowforge.engine.runner import run_pipeline

    with app.app_context():
        try:
            try:
                steps, pipeline_vars, secret_keys = load_pipeline(pipeline_id)
            except Exception as e:
                logger.exception("Failed to load pipeline %s", pipeline_name)
                _mark_failed(run_id, f'Failed to load pipeline: {e}')
                return

            pipeline = db.session.get(Pipeline, pipeline_id)
            webhook_url = pipeline.on_failure_webhook_url if pipeline else None

            run_pipeline(
                pipeline_name=pipeline_name,
                steps=steps,
                pipeline_vars=pipeline_vars,
                triggered_by=triggered_by,
                pipeline_id=pipeline_id,
                existing_run_id=run_id,
                secret_var_keys=secret_keys,
                on_failure_webhook_url=webhook_url,
            )
        finally:
            concurrency.release(token)


def _mark_failed(run_id: str, message: str) -> None:
    from datetime import datetime
    try:
        run = db.session.get(PipelineRun, run_id)
        if run:
            run.status = 'failed'
            run.error_message = message
            run.finished_at = datetime.now(UTC)
            db.session.commit()
    except Exception:
        logger.exception("Could not mark run %s as failed", run_id)
