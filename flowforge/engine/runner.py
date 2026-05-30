import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from flowforge import audit
from flowforge.engine import shutdown
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
    error_step: str = ''
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


def _get_retry_config(step: BaseStep) -> tuple[int, int]:
    cfg = step.config if hasattr(step, 'config') else {}
    count = max(0, min(int(cfg.get('retry_count', 0)), 10))
    delay = max(0, min(int(cfg.get('retry_delay_seconds', 30)), 3600))
    return count, delay


def _run_step_with_retry(
    pipeline_name: str,
    step: BaseStep,
    context: dict,
    retry_count: int,
    retry_delay: int,
) -> StepResult:
    attempt = 0
    while True:
        try:
            step_result = step.run(context)
        except Exception as e:
            logger.exception("[%s] Step '%s' raised uncaught exception", pipeline_name, step.name)
            step_result = StepResult(success=False, error=str(e))
        if step_result.success or attempt >= retry_count:
            return step_result
        attempt += 1
        logger.warning(
            "[%s] Step '%s' failed (attempt %d/%d), retrying in %ds. Error: %s",
            pipeline_name, step.name, attempt, retry_count + 1, retry_delay, step_result.error,
        )
        time.sleep(retry_delay)


def _expose_step_outputs(context: dict, pipeline_name: str, step_name: str, step_result: StepResult) -> None:
    context['steps'][step_name] = {
        'output_path':    step_result.output_path,
        'drive_url':      step_result.drive_url,
        'rows_affected':  step_result.rows_affected,
        'files_found':    step_result.files_found,
        'files_loaded':   step_result.files_loaded,
        'files_failed':   step_result.files_failed,
        'records_loaded': step_result.records_loaded,
        'records_failed': step_result.records_failed,
        'duration_sec':   step_result.duration_sec,
        'rows':           step_result.rows,
        'table_html':     step_result.table_html,
        'kv_html':        step_result.kv_html,
        'ai_summary':     step_result.ai_summary,
    }
    if step_result.output_variables:
        collisions = _CONTEXT_META_KEYS & step_result.output_variables.keys()
        if collisions:
            logger.warning(
                "[%s] Step '%s' tried to overwrite reserved variable(s): %s — skipping.",
                pipeline_name, step_name, sorted(collisions),
            )
        context.update({k: v for k, v in step_result.output_variables.items()
                        if k not in _CONTEXT_META_KEYS})


def _handle_failed_step(
    result: PipelineResult,
    pipeline_name: str,
    step: BaseStep,
    step_result: StepResult,
    run_record: Any,
) -> bool:
    """Apply failure logic; return True if pipeline should stop."""
    if step.on_error == 'stop':
        logger.error(
            "[%s] Step '%s' failed (on_error=stop). Error: %s",
            pipeline_name, step.name, step_result.error,
        )
        result.error = step_result.error
        result.error_step = step.name
        _finish_run_record(run_record, success=False, error_step=step.name,
                           error_message=step_result.error)
        return True
    logger.warning(
        "[%s] Step '%s' failed (on_error=continue). Error: %s",
        pipeline_name, step.name, step_result.error,
    )
    if not result.error:
        result.error = step_result.error
    return False


def run_pipeline(
    pipeline_name: str,
    steps: list[BaseStep],
    pipeline_vars: dict[str, str] | None = None,
    triggered_by: str = 'api',
    pipeline_id: str | None = None,
    existing_run_id: str | None = None,
    secret_var_keys: set[str] | None = None,
    on_failure_webhook_url: str | None = None,
) -> PipelineResult:
    """Execute an ordered list of steps, threading context between them."""
    from flowforge.engine.context import build

    if pipeline_id:
        pipeline_vars = dict(pipeline_vars or {})
        pipeline_vars.setdefault('last_success_at',   _get_last_success_ts(pipeline_id, '%Y%m%d%H%M%S'))
        pipeline_vars.setdefault('last_success_date', _get_last_success_ts(pipeline_id, '%Y-%m-%d'))

    context = build(pipeline_name, pipeline_vars=pipeline_vars)
    context['triggered_by'] = triggered_by
    context['_pipeline_has_failed'] = False
    vars_log = _build_vars_log(context, secret_var_keys)

    result = PipelineResult(success=True, pipeline_name=pipeline_name)

    run_record = _create_run_record(pipeline_id, pipeline_name, triggered_by, existing_run_id)
    if run_record:
        result.run_id = run_record.id
        context['run_id'] = run_record.id
        shutdown.register_run(run_record.id)

    audit.log_pipeline_run(pipeline_name, triggered_by, result.run_id or context['run_id'], 'STARTED')

    step_order = 0
    try:
        for step in steps:
            step_order += 1
            logger.info("[%s] Starting step: %s", pipeline_name, step.name)
            retry_count, retry_delay = _get_retry_config(step)
            step_start = datetime.now(timezone.utc)
            step_result = _run_step_with_retry(pipeline_name, step, context, retry_count, retry_delay)
            step_end = datetime.now(timezone.utc)
            duration_ms = int((step_end - step_start).total_seconds() * 1000)
            result.step_results[step.name] = step_result
            result.steps_run += 1
            _expose_step_outputs(context, pipeline_name, step.name, step_result)
            _write_step_run(run_record, step, step_order, step_result, step_start, step_end, duration_ms, vars_log)
            if not step_result.success:
                result.steps_failed += 1
                result.success = False
                context['_pipeline_has_failed'] = True
                if _handle_failed_step(result, pipeline_name, step, step_result, run_record):
                    break
        else:
            if result.success:
                logger.info("[%s] Pipeline completed (%d steps)", pipeline_name, result.steps_run)
            _finish_run_record(run_record, success=result.success)
    finally:
        if run_record:
            shutdown.unregister_run(run_record.id)

    if not result.success and result.steps_run < len(steps):
        logger.error("[%s] Pipeline failed after %d/%d steps", pipeline_name, result.steps_run, len(steps))

    audit.log_pipeline_run(
        pipeline_name, triggered_by, result.run_id or context['run_id'],
        'SUCCESS' if result.success else 'FAILED',
    )

    if not result.success and on_failure_webhook_url:
        _fire_failure_webhook(on_failure_webhook_url, {
            'pipeline_name': pipeline_name,
            'run_id':        result.run_id or context.get('run_id', ''),
            'error_step':    result.error_step,
            'error_message': result.error,
            'triggered_by':  triggered_by,
        })

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
    except SQLAlchemyError:
        logger.exception("Failed to create pipeline_run record")
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
    except SQLAlchemyError:
        logger.exception("Failed to write step_run record")


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
    except SQLAlchemyError:
        logger.exception("Failed to update pipeline_run record")


def _fire_failure_webhook(url: str, payload: dict) -> None:
    """POST JSON payload to the failure webhook URL; errors are logged, never raised."""
    if not url:
        return
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10):  # nosec B310
            pass
        logger.info("Failure webhook delivered to %s", url)
    except Exception as exc:
        logger.warning("Failure webhook POST to %s failed: %s", url, exc)


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
