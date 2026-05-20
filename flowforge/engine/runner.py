import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from flowforge import audit
from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    success: bool
    pipeline_name: str
    steps_run: int = 0
    steps_failed: int = 0
    step_results: dict[str, StepResult] = field(default_factory=dict)
    error: str = ''
    run_id: str = ''


_BUILT_IN_VAR_KEYS = (
    'current_date', 'current_month', 'current_year', 'yesterday',
    'week_start', 'week_end', 'month_start', 'month_end',
    'quarter_start', 'quarter_end', 'timestamp', 'run_id', 'pipeline_name',
)
_CONTEXT_META_KEYS = frozenset(_BUILT_IN_VAR_KEYS) | {'env', 'steps', 'triggered_by', 'vars'}


def _build_vars_log(context: dict, secret_keys: set[str] | None) -> str:
    secret_keys = secret_keys or set()
    sep = '─' * 42
    lines = [sep, 'Variables resolved:']
    for key in _BUILT_IN_VAR_KEYS:
        if key in context:
            lines.append(f'  {key:<20} {context[key]}')
    for key, val in context.items():
        if key not in _CONTEXT_META_KEYS:
            lines.append(f'  {key:<20} {"***" if key in secret_keys else val}')
    lines.append(sep)
    return '\n'.join(lines)


def run_pipeline(
    pipeline_name: str,
    steps: list[BaseStep],
    pipeline_vars: dict[str, str] | None = None,
    triggered_by: str = 'api',
    pipeline_id: str | None = None,
    existing_run_id: str | None = None,
    secret_var_keys: set[str] | None = None,
) -> PipelineResult:
    """Execute an ordered list of steps, threading context between them."""
    from flowforge.engine.context import build

    context = build(pipeline_name, pipeline_vars=pipeline_vars)
    context['triggered_by'] = triggered_by
    vars_log = _build_vars_log(context, secret_var_keys)

    result = PipelineResult(success=True, pipeline_name=pipeline_name)

    # Create pipeline_run record if we have a DB context available
    run_record = _create_run_record(pipeline_id, pipeline_name, triggered_by, existing_run_id)
    if run_record:
        result.run_id = run_record.id
        context['run_id'] = run_record.id  # overwrite uuid4() placeholder with real DB run ID

    audit.log_pipeline_run(pipeline_name, triggered_by, result.run_id or context['run_id'], 'STARTED')

    step_order = 0
    for step in steps:
        step_order += 1
        logger.info("[%s] Starting step: %s", pipeline_name, step.name)

        step_start = datetime.now(timezone.utc)
        try:
            step_result = step.run(context)
        except Exception as e:
            logger.error("[%s] Step '%s' raised uncaught exception: %s", pipeline_name, step.name, e)
            step_result = StepResult(success=False, error=str(e))

        step_end = datetime.now(timezone.utc)
        duration_ms = int((step_end - step_start).total_seconds() * 1000)

        result.step_results[step.name] = step_result
        result.steps_run += 1

        # Expose this step's outputs to downstream steps via {{ steps.name.* }}
        context['steps'][step.name] = {
            'output_path':   step_result.output_path,
            'drive_url':     step_result.drive_url,
            'rows_affected': step_result.rows_affected,
        }

        # Scalar output variables go to top-level context; guard against overwriting built-ins
        if step_result.output_variables:
            collisions = _CONTEXT_META_KEYS & step_result.output_variables.keys()
            if collisions:
                logger.warning(
                    "[%s] Step '%s' tried to overwrite reserved variable(s): %s — skipping.",
                    pipeline_name, step.name, sorted(collisions),
                )
            context.update({k: v for k, v in step_result.output_variables.items()
                            if k not in _CONTEXT_META_KEYS})

        _write_step_run(run_record, step, step_order, step_result, step_start, step_end, duration_ms, vars_log)

        if not step_result.success:
            result.steps_failed += 1
            if step.on_error == 'stop':
                logger.error(
                    "[%s] Step '%s' failed (on_error=stop). Error: %s",
                    pipeline_name, step.name, step_result.error,
                )
                result.success = False
                result.error = step_result.error
                _finish_run_record(run_record, success=False, error_step=step.name,
                                   error_message=step_result.error)
                break
            logger.warning(
                "[%s] Step '%s' failed (on_error=continue). Error: %s",
                pipeline_name, step.name, step_result.error,
            )
    else:
        # Loop completed without break — all steps attempted
        if result.success:
            logger.info("[%s] Pipeline completed (%d steps)", pipeline_name, result.steps_run)
        _finish_run_record(run_record, success=result.success)

    if not result.success and result.steps_run < len(steps):
        logger.error("[%s] Pipeline failed after %d/%d steps", pipeline_name, result.steps_run, len(steps))

    audit.log_pipeline_run(
        pipeline_name, triggered_by, result.run_id or context['run_id'],
        'SUCCESS' if result.success else 'FAILED',
    )
    return result


# ─────────────────────────────────────────
# DB helpers — silently no-op if no app context
# ─────────────────────────────────────────

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
    except SQLAlchemyError as e:
        logger.error("Failed to create pipeline_run record: %s", e)
        return None


def _write_step_run(run_record, step, step_order, step_result, started_at, finished_at, duration_ms, vars_log=''):
    if not run_record:
        return
    try:
        from flowforge.db.models import StepRun, db
        combined_logs = '\n\n'.join(filter(None, [vars_log, step_result.logs])) or None
        sr = StepRun(
            pipeline_run_id=run_record.id,
            step_name=step.name,
            step_type=step.step_type or step.__class__.__name__.replace('Step', '').lower(),
            step_order=step_order,
            status='success' if step_result.success else 'failed',
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            rows_affected=step_result.rows_affected or None,
            output_path=step_result.output_path or None,
            drive_url=step_result.drive_url or None,
            email_sent_to=step_result.extra.get('email_sent_to') if step_result.extra else None,
            logs=combined_logs,
            error_message=step_result.error or None,
        )
        db.session.add(sr)
        db.session.commit()
    except SQLAlchemyError as e:
        logger.error("Failed to write step_run record: %s", e)


def _finish_run_record(run_record, success: bool, error_step: str = '', error_message: str = ''):
    if not run_record:
        return
    try:
        from flowforge.db.models import db
        run_record.status = 'success' if success else 'failed'
        run_record.finished_at = datetime.now(timezone.utc)
        if run_record.started_at:
            run_record.duration_ms = int(
                (run_record.finished_at - run_record.started_at).total_seconds() * 1000
            )
        if error_step:
            run_record.error_step = error_step
        if error_message:
            run_record.error_message = error_message
        db.session.commit()
    except SQLAlchemyError as e:
        logger.error("Failed to update pipeline_run record: %s", e)
