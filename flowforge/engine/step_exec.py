"""Single-step execution primitives shared by both orchestration engines.

Extracted out of engine/runner.py so that engine/dag.py (the DAG execution
engine) doesn't need to import engine/runner.py (the wave execution engine)
to get PipelineResult / _run_step_with_retry / _write_step_run / etc. — before
this module existed, dag.py imported those names directly from runner.py at
module level, while runner.py imported dag.py's run_dag() lazily inside a
function body specifically to dodge the resulting circular import. Both
engines now depend on this lower-level module instead of on each other.
"""
import logging
import time
from dataclasses import dataclass, field

from sqlalchemy.exc import SQLAlchemyError

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


def _write_step_run(run_record, step, step_order, step_result, started_at, finished_at, duration_ms,
                    vars_log='', skipped=False):
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
            status='skipped' if skipped else ('success' if step_result.success else 'failed'),
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
