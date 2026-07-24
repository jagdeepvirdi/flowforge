import concurrent.futures
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from flowforge import audit
from flowforge.engine import shutdown
from flowforge.engine.step_exec import (
    _BUILT_IN_VAR_KEYS,
    _CONTEXT_META_KEYS,
    PipelineResult,
    _get_retry_config,
    _run_step_with_retry,
    _write_step_run,
)
from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


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


def _build_execution_waves(steps: list[BaseStep]) -> list[list[BaseStep]]:
    """Group steps into sequential waves; steps sharing the same parallel_group run concurrently."""
    waves: list[list[BaseStep]] = []
    i = 0
    while i < len(steps):
        step = steps[i]
        pg = step.parallel_group
        if not pg:
            waves.append([step])
            i += 1
        else:
            group: list[BaseStep] = [step]
            i += 1
            while i < len(steps) and steps[i].parallel_group == pg:
                group.append(steps[i])
                i += 1
            waves.append(group)
    return waves


def _run_parallel_wave(
    wave: list[BaseStep],
    context: dict,
    result: PipelineResult,
    run_record: Any,
    pipeline_name: str,
    vars_log: str,
) -> bool:
    """Run all steps in a parallel wave concurrently.

    Returns True if the pipeline should stop (any step with on_error=stop failed).
    Context is updated in-place with merged outputs after all steps complete.
    """
    n = len(wave)
    # Each thread gets its own shallow context snapshot
    snapshots = [{**context, 'steps': dict(context.get('steps', {}))} for _ in range(n)]
    step_results: list[StepResult | None] = [None] * n
    step_times:   list[tuple[datetime, datetime] | None] = [None] * n

    def _run_one(idx: int) -> None:
        step = wave[idx]
        retry_count, retry_delay = _get_retry_config(step)
        t0 = datetime.now(UTC)
        step_results[idx] = _run_step_with_retry(pipeline_name, step, snapshots[idx], retry_count, retry_delay)
        step_times[idx] = (t0, datetime.now(UTC))

    with concurrent.futures.ThreadPoolExecutor(max_workers=n, thread_name_prefix='ff_parallel') as executor:
        futures = [executor.submit(_run_one, i) for i in range(n)]
        concurrent.futures.wait(futures)

    # Propagate any uncaught exceptions from threads (shouldn't happen — _run_step_with_retry catches all)
    for f in futures:
        if f.exception():
            logger.error("[%s] Parallel step raised an unexpected exception: %s", pipeline_name, f.exception())

    should_stop = False
    for i, (step, step_result) in enumerate(zip(wave, step_results)):
        if step_result is None:
            step_result = StepResult(success=False, error='Step did not produce a result')
            step_results[i] = step_result

        t0, t1 = step_times[i] or (datetime.now(UTC), datetime.now(UTC))
        duration_ms = int((t1 - t0).total_seconds() * 1000)

        result.step_results[step.name] = step_result
        result.steps_run += 1
        _expose_step_outputs(context, pipeline_name, step.name, step_result)
        _write_step_run(run_record, step, step.db_step_order or (i + 1),
                        step_result, t0, t1, duration_ms,
                        vars_log if i == 0 else '')

        if not step_result.success:
            result.steps_failed += 1
            result.success = False
            context['_pipeline_has_failed'] = True
            if step.on_error == 'stop':
                logger.error("[%s] Parallel step '%s' failed (on_error=stop).", pipeline_name, step.name)
                if not result.error:
                    result.error      = step_result.error
                    result.error_step = step.name
                should_stop = True
            else:
                logger.warning("[%s] Parallel step '%s' failed (on_error=continue).", pipeline_name, step.name)
                if not result.error:
                    result.error = step_result.error

    return should_stop


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
                    step = wave[0]
                    logger.info("[%s] Starting step: %s", pipeline_name, step.name)
                    retry_count, retry_delay = _get_retry_config(step)
                    step_start = datetime.now(UTC)
                    step_result = _run_step_with_retry(pipeline_name, step, context, retry_count, retry_delay)
                    step_end = datetime.now(UTC)
                    duration_ms = int((step_end - step_start).total_seconds() * 1000)
                    result.step_results[step.name] = step_result
                    result.steps_run += 1
                    _expose_step_outputs(context, pipeline_name, step.name, step_result)
                    _write_step_run(run_record, step, step.db_step_order or wave_num,
                                    step_result, step_start, step_end, duration_ms, vars_log)
                    vars_log = ''  # only include var dump in the first step's logs
                    if not step_result.success:
                        result.steps_failed += 1
                        result.success = False
                        context['_pipeline_has_failed'] = True
                        if _handle_failed_step(result, pipeline_name, step, step_result, run_record):
                            pipeline_stopped = True
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


# ─────────────────────────────────────────
# Pipeline dependency trigger
# ─────────────────────────────────────────

def _trigger_downstream_pipelines(pipeline_id: str) -> None:
    """After a successful run, check and launch eligible downstream pipelines.

    A downstream pipeline is eligible when ALL its upstream dependencies have
    a successful run that completed after the downstream's last run started
    (or ever, if the downstream has never run).
    """
    try:
        from flowforge.db.models import Pipeline, PipelineDependency, PipelineRun, db
        from flowforge.engine.launcher import launch_run

        # Find all downstream pipelines that list this pipeline as an upstream
        fanout = db.session.query(PipelineDependency).filter_by(upstream_id=pipeline_id).all()
        if not fanout:
            return

        for dep in fanout:
            downstream_id = dep.downstream_id
            downstream = db.session.get(Pipeline, downstream_id)
            if not downstream or not downstream.enabled:
                continue

            # When did downstream last run?
            last_run = (
                db.session.query(PipelineRun)
                .filter_by(pipeline_id=downstream_id)
                .order_by(PipelineRun.started_at.desc())
                .first()
            )
            since = last_run.started_at if last_run else None

            # Check ALL upstreams of that downstream have a success run after `since`
            all_upstream_deps = (
                db.session.query(PipelineDependency)
                .filter_by(downstream_id=downstream_id)
                .all()
            )
            all_satisfied = True
            for up_dep in all_upstream_deps:
                q = (
                    db.session.query(PipelineRun)
                    .filter_by(pipeline_id=up_dep.upstream_id, status='success')
                )
                if since is not None:
                    q = q.filter(PipelineRun.finished_at > since)
                if not q.first():
                    all_satisfied = False
                    break

            if all_satisfied:
                logger.info(
                    "Dependency trigger: launching '%s' (all upstreams satisfied)",
                    downstream.name,
                )
                try:
                    launch_run(downstream, triggered_by='dependency')
                except Exception:
                    logger.exception("Failed to trigger downstream pipeline '%s'", downstream.name)
    except Exception:
        logger.exception("Error in _trigger_downstream_pipelines for pipeline %s", pipeline_id)


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


def _notify_devbrain(
    pipeline_name: str, run_id: str, success: bool,
    error_step: str = '', error_message: str = '',
) -> None:
    """POST a run-completion notification to DevBrain's /api/notify hook.

    Gated by FLOWFORGE_DEVBRAIN_NOTIFY_URL (e.g. http://localhost:3001/api/notify) — unset by
    default, so this is a no-op unless the operator has DevBrain running and wants pipeline
    completions surfaced there. Fires on every run (success and failure), unlike
    on_failure_webhook_url above which is failure-only and per-pipeline-configured. Errors are
    logged, never raised — a notification failure must never fail a pipeline run.
    """
    url = os.environ.get('FLOWFORGE_DEVBRAIN_NOTIFY_URL', '')
    if not url:
        return
    if success:
        title = f'Pipeline succeeded: {pipeline_name}'
        body = f'Run {run_id} completed successfully.'
    else:
        title = f'Pipeline failed: {pipeline_name}'
        body = f"Run {run_id} failed at step '{error_step}': {error_message}"
    payload = {
        'project': 'flowforge',
        'title':   title,
        'body':    body,
        'level':   'success' if success else 'error',
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10):  # nosec B310
            pass
        logger.info("DevBrain notification delivered for pipeline %s", pipeline_name)
    except Exception as exc:
        logger.warning("DevBrain notification POST to %s failed: %s", url, exc)


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
