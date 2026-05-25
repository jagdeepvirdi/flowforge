import logging
from datetime import datetime, timezone

from flowforge.celery_app import celery
from flowforge.db.models import Pipeline, PipelineRun, db
from flowforge.engine.loader import load_pipeline
from flowforge.engine.runner import run_pipeline

logger = logging.getLogger(__name__)

@celery.task(bind=True, name='flowforge.run_pipeline_task')
def run_pipeline_task(self, pipeline_id: str, triggered_by: str, run_id: str):
    """Celery task to execute a pipeline."""
    from flowforge.api.app import create_app
    app = create_app()

    with app.app_context():
        pipeline = db.session.get(Pipeline, pipeline_id)
        if not pipeline:
            logger.error("Pipeline %s not found in task", pipeline_id)
            return

        try:
            steps, pipeline_vars, secret_keys = load_pipeline(pipeline_id)
        except Exception as e:
            run = db.session.get(PipelineRun, run_id)
            if run:
                run.status = 'failed'
                run.error_message = f'Failed to load pipeline: {e}'
                run.finished_at = datetime.now(timezone.utc)
                db.session.commit()
            return

        run_pipeline(
            pipeline_name=pipeline.name,
            steps=steps,
            pipeline_vars=pipeline_vars,
            triggered_by=triggered_by,
            pipeline_id=pipeline_id,
            existing_run_id=run_id,
            secret_var_keys=secret_keys,
            on_failure_webhook_url=pipeline.on_failure_webhook_url,
        )
