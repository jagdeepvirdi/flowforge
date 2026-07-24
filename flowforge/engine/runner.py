import logging

from sqlalchemy.exc import SQLAlchemyError

from flowforge import audit
from flowforge.engine import shutdown
from flowforge.engine.dependency_trigger import _trigger_downstream_pipelines
from flowforge.engine.notifications import _fire_failure_webhook, _notify_devbrain
from flowforge.engine.run_records import (
    _create_run_record,
    _finish_run_record,
    _get_last_success_ts,
)
from flowforge.engine.step_exec import (
    PipelineResult,
    _write_step_run,  # noqa: F401 — re-exported, see note below
)
from flowforge.engine.waves import (
    _build_execution_waves,
    _build_vars_log,
    _expose_step_outputs,  # noqa: F401 — re-exported, see note below
    _handle_failed_step,  # noqa: F401 — re-exported, see note below
    _run_parallel_wave,
    _run_sequential_step,
)

# _write_step_run / _expose_step_outputs / _handle_failed_step aren't called directly in this
# module anymore (that now happens inside waves.py) but are kept bound here, unused, because
# existing tests patch/import them as `flowforge.engine.runner.<name>` — see the same convention
# used for step_exec's other re-exports after the dag.py/runner.py circular-import fix.

logger = logging.getLogger(__name__)


def run_pipeline(
    pipeline_name: str,
    steps: list,
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
    context['_secret_var_keys'] = secret_var_keys or set()
    vars_log = _build_vars_log(context, secret_var_keys)

    result = PipelineResult(success=True, pipeline_name=pipeline_name)

    run_record = _create_run_record(pipeline_id, pipeline_name, triggered_by, existing_run_id)
    if run_record:
        result.run_id = run_record.id
        context['run_id'] = run_record.id
        shutdown.register_run(run_record.id)

    audit.log_pipeline_run(pipeline_name, triggered_by, result.run_id or context['run_id'], 'STARTED')

    # Dual-path engine gate (Phase 14 Option B, Milestone 2): a pipeline with zero
    # StepDependency rows keeps running through the wave engine below, byte-for-byte
    # unchanged. The DAG engine only activates once a pipeline actually has step-level edges.
    use_dag_engine = False
    step_dep_edges: list[tuple[str, str]] = []
    if pipeline_id:
        try:
            from flowforge.db.models import StepDependency, db
            if StepDependency.exists_for_pipeline(pipeline_id):
                use_dag_engine = True
                step_dep_edges = [
                    (e.upstream_step_id, e.downstream_step_id)
                    for e in db.session.query(StepDependency).filter_by(pipeline_id=pipeline_id).all()
                ]
        except SQLAlchemyError:
            logger.exception(
                "[%s] Failed to check step dependencies; falling back to wave engine", pipeline_name,
            )

    try:
        if use_dag_engine:
            from flowforge.engine.dag import run_dag
            logger.info("[%s] Step dependencies found — using DAG execution engine", pipeline_name)
            run_dag(steps, step_dep_edges, context, result, run_record, pipeline_name, vars_log)
            if result.success:
                logger.info("[%s] Pipeline completed (%d steps)", pipeline_name, result.steps_run)
            _finish_run_record(run_record, success=result.success,
                               error_step=result.error_step, error_message=result.error)
        else:
            waves = _build_execution_waves(steps)
            wave_num = 0
            pipeline_stopped = False
            for wave in waves:
                wave_num += 1
                if len(wave) == 1:
                    # ── Sequential step ────────────────────────────────────────
                    pipeline_stopped = _run_sequential_step(
                        wave[0], context, result, run_record, pipeline_name, vars_log, wave_num,
                    )
                    vars_log = ''  # only include var dump in the first step's logs
                    if pipeline_stopped:
                        break
                else:
                    # ── Parallel wave ─────────────────────────────────────────
                    names = ', '.join(s.name for s in wave)
                    logger.info("[%s] Starting parallel wave (%d steps): %s", pipeline_name, len(wave), names)
                    should_stop = _run_parallel_wave(wave, context, result, run_record, pipeline_name, vars_log)
                    vars_log = ''
                    if should_stop:
                        _finish_run_record(run_record, success=False,
                                           error_step=result.error_step,
                                           error_message=result.error)
                        pipeline_stopped = True
                        break

            if not pipeline_stopped:
                if result.success:
                    logger.info("[%s] Pipeline completed (%d steps)", pipeline_name, result.steps_run)
                _finish_run_record(run_record, success=result.success)
    finally:
        if run_record:
            shutdown.unregister_run(run_record.id)

    total_steps = len(steps)
    if not result.success and result.steps_run < total_steps:
        logger.error("[%s] Pipeline failed after %d/%d steps", pipeline_name, result.steps_run, total_steps)

    audit.log_pipeline_run(
        pipeline_name, triggered_by, result.run_id or context['run_id'],
        'SUCCESS' if result.success else 'FAILED',
    )

    _notify_devbrain(
        pipeline_name, result.run_id or context.get('run_id', ''), result.success,
        error_step=result.error_step, error_message=result.error,
    )

    if result.success and pipeline_id:
        _trigger_downstream_pipelines(pipeline_id)

    if not result.success and on_failure_webhook_url:
        _fire_failure_webhook(on_failure_webhook_url, {
            'pipeline_name': pipeline_name,
            'run_id':        result.run_id or context.get('run_id', ''),
            'error_step':    result.error_step,
            'error_message': result.error,
            'triggered_by':  triggered_by,
        })

    return result
