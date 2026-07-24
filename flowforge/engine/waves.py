"""Wave-building and wave execution for the sequential/parallel ("wave") pipeline engine.

A pipeline's steps are grouped into ordered waves; a wave of one step runs
sequentially, a wave of steps sharing the same parallel_group runs
concurrently in a thread pool. This is the default engine — the DAG engine
(engine/dag.py) only takes over once a pipeline has step-level dependency
edges (see engine/runner.py's run_pipeline()).
"""
import concurrent.futures
import logging
from datetime import UTC, datetime
from typing import Any

from flowforge.engine.run_records import _finish_run_record
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


def _run_sequential_step(
    step: BaseStep,
    context: dict,
    result: PipelineResult,
    run_record: Any,
    pipeline_name: str,
    vars_log: str,
    wave_num: int,
) -> bool:
    """Run a single non-parallel step. Returns True if the pipeline should stop."""
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
    if not step_result.success:
        result.steps_failed += 1
        result.success = False
        context['_pipeline_has_failed'] = True
        return _handle_failed_step(result, pipeline_name, step, step_result, run_record)
    return False


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
