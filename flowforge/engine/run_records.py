"""pipeline_run / step_run DB record helpers used by the runner.

Silently no-op (or return an empty value) when there's no app context or the
DB write fails — a run-record bookkeeping error must never fail the pipeline
run it's trying to record.
"""
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def _create_run_record(pipeline_id, pipeline_name, triggered_by, existing_run_id=None):
    try:
        from flowforge.db.models import PipelineRun, db
        if existing_run_id:
            return db.session.get(PipelineRun, existing_run_id)
        run = PipelineRun(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            status='running',
            triggered_by=triggered_by,
        )
        db.session.add(run)
        db.session.commit()
        return run
    except SQLAlchemyError:
        logger.exception("Failed to create pipeline_run record")
        return None


def _finish_run_record(run_record, success: bool, error_step: str = '', error_message: str = ''):
    if not run_record:
        return
    try:
        from flowforge.db.models import db
        run_record.status = 'success' if success else 'failed'
        run_record.finished_at = datetime.now(UTC)
        if run_record.started_at:
            run_record.duration_ms = int(
                (run_record.finished_at - run_record.started_at).total_seconds() * 1000
            )
        if error_step:
            run_record.error_step = error_step
        if error_message:
            run_record.error_message = error_message
        db.session.commit()
    except SQLAlchemyError:
        logger.exception("Failed to update pipeline_run record")


def _get_last_success_ts(pipeline_id: str, fmt: str) -> str:
    """Return the finished_at of the most recent successful run in the given strftime format.

    Returns an empty string if no successful run exists or DB is unavailable.
    Used to populate {{ last_success_at }} and {{ last_success_date }} in context.
    """
    try:
        from flowforge.db.models import PipelineRun, db
        run = (
            db.session.query(PipelineRun)
            .filter_by(pipeline_id=pipeline_id, status='success')
            .order_by(PipelineRun.finished_at.desc())
            .first()
        )
        if run and run.finished_at:
            return run.finished_at.strftime(fmt)
        return ''
    except Exception as e:
        logger.warning("Could not fetch last_success_ts for pipeline %s: %s", pipeline_id, e)
        return ''
