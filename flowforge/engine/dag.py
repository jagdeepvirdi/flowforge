"""Topological (in-degree/ready-set) DAG execution engine.

Phase 14 Option B, Milestone 2. Only invoked by `runner.run_pipeline`'s dual-path gate when
`StepDependency.exists_for_pipeline(pipeline_id)` is True — a pipeline with zero step-level
edges keeps running through `runner._build_execution_waves`'s wave engine, untouched.

Design, locked in with the user 2026-07-21 (see docs/TASKS.md Phase 14.2):
  - Steps dispatch as soon as their upstream dependencies complete, not in synchronized batches.
  - `on_error='stop'` is branch-scoped: a failed step skips only its transitive descendants;
    unrelated/independent branches keep running to completion.
  - Context visibility is ancestors-only: a step's `{{ steps.X.* }}` and flattened
    `output_variables` are populated only from its transitive-ancestor steps, not "everything
    completed so far" pipeline-wide.
  - A `StepDependency` edge referencing a disabled (unloaded) step is dropped rather than
    honored or rejected — "skip-and-satisfy": a downstream step never waits on a step that will
    never run.
"""
import concurrent.futures
import logging
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any

from flowforge.engine.step_exec import (
    _CONTEXT_META_KEYS,
    PipelineResult,
    _get_retry_config,
    _run_step_with_retry,
    _write_step_run,
)
from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


def _transitive_closure(start: str, adjacency: dict[str, list[str]]) -> set[str]:
    """All nodes reachable from `start` by following `adjacency` edges (excludes `start` itself)."""
    visited: set[str] = set()
    stack = list(adjacency.get(start, []))
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        stack.extend(adjacency.get(node, []))
    return visited


def _step_output_entry(step_result: StepResult) -> dict:
    """The `context['steps'][name]` sub-dict for one step's result.

    Deliberately duplicated from runner._expose_step_outputs (which mutates a single shared
    context in place — wrong model here, where each node needs an ancestors-only view) rather
    than refactored to share code, so the wave engine's behavior/signature stays byte-for-byte
    unchanged per the Milestone 1 backward-compatibility decision.
    """
    return {
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


def _step_output_vars(pipeline_name: str, step_name: str, step_result: StepResult) -> dict:
    """Flattened top-level `output_variables` contributed by one step, minus reserved keys."""
    if not step_result.output_variables:
        return {}
    collisions = _CONTEXT_META_KEYS & step_result.output_variables.keys()
    if collisions:
        logger.warning(
            "[%s] Step '%s' tried to overwrite reserved variable(s): %s — skipping.",
            pipeline_name, step_name, sorted(collisions),
        )
    return {k: v for k, v in step_result.output_variables.items() if k not in _CONTEXT_META_KEYS}


def run_dag(
    steps: list[BaseStep],
    edges: list[tuple[str, str]],
    context: dict[str, Any],
    result: PipelineResult,
    run_record: Any,
    pipeline_name: str,
    vars_log: str,
) -> None:
    """Execute `steps` per the DAG defined by `edges` (upstream_step_id, downstream_step_id).

    Mutates `result` and `context['_pipeline_has_failed']` in place and writes step_run rows,
    mirroring the wave engine's side effects, so callers (runner.run_pipeline) can post-process
    identically regardless of which engine ran.
    """
    id_to_step = {s.db_step_id: s for s in steps if s.db_step_id}
    valid_ids = set(id_to_step)
    step_name_by_id = {sid: s.name for sid, s in id_to_step.items()}

    adjacency: dict[str, list[str]] = defaultdict(list)
    reverse_adjacency: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = dict.fromkeys(valid_ids, 0)

    dropped = 0
    for upstream_id, downstream_id in edges:
        if upstream_id not in valid_ids or downstream_id not in valid_ids:
            # References a disabled/unloaded step — skip-and-satisfy (see module docstring).
            dropped += 1
            continue
        adjacency[upstream_id].append(downstream_id)
        reverse_adjacency[downstream_id].append(upstream_id)
        in_degree[downstream_id] += 1
    if dropped:
        logger.warning(
            "[%s] %d step-dependency edge(s) reference a disabled or missing step and were ignored",
            pipeline_name, dropped,
        )

    ancestors_of   = {sid: _transitive_closure(sid, reverse_adjacency) for sid in valid_ids}
    descendants_of = {sid: _transitive_closure(sid, adjacency) for sid in valid_ids}

    completed_step_entry: dict[str, dict] = {}
    completed_vars: dict[str, dict] = {}
    skip_ids: set[str] = set()
    pending: set[str] = set(valid_ids)

    ready: deque[str] = deque(
        sorted((sid for sid in valid_ids if in_degree[sid] == 0),
              key=lambda sid: id_to_step[sid].db_step_order)
    )
    vars_log_remaining = vars_log

    def _build_node_context(sid: str) -> dict:
        node_ctx = {**context}
        node_ctx['steps'] = {
            step_name_by_id[aid]: completed_step_entry[aid]
            for aid in ancestors_of[sid] if aid in completed_step_entry
        }
        for aid in sorted(ancestors_of[sid], key=lambda i: id_to_step[i].db_step_order):
            node_ctx.update(completed_vars.get(aid, {}))
        return node_ctx

    def _run_node(sid: str, node_vars_log: str):
        step = id_to_step[sid]
        retry_count, retry_delay = _get_retry_config(step)
        node_ctx = _build_node_context(sid)
        t0 = datetime.now(UTC)
        step_result = _run_step_with_retry(pipeline_name, step, node_ctx, retry_count, retry_delay)
        t1 = datetime.now(UTC)
        return sid, step_result, t0, t1, node_vars_log

    def _finalize_skip(sid: str) -> None:
        """Mark `sid` as skipped without touching in-degree/ready bookkeeping.

        Safe to do unconditionally: `sid` is a transitive descendant of a just-failed
        `on_error=stop` step, so by construction none of its own downstream edges lead
        anywhere outside that same descendant set — there is nothing left to propagate to
        that this pass doesn't already cover.
        """
        step = id_to_step[sid]
        now = datetime.now(UTC)
        step_result = StepResult(success=False, error="Skipped: an upstream step failed (on_error=stop)")
        result.step_results[step.name] = step_result
        _write_step_run(run_record, step, step.db_step_order, step_result, now, now, 0, '', skipped=True)
        pending.discard(sid)

    in_flight: dict[concurrent.futures.Future, str] = {}
    max_workers = max(1, len(valid_ids))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='ff_dag') as executor:
        while pending:
            while ready:
                sid = ready.popleft()
                if sid in skip_ids:
                    _finalize_skip(sid)
                    continue
                node_vars_log, vars_log_remaining = vars_log_remaining, ''
                future = executor.submit(_run_node, sid, node_vars_log)
                in_flight[future] = sid

            if not in_flight:
                break  # nothing ready and nothing running — shouldn't happen on an acyclic graph

            done, _ = concurrent.futures.wait(list(in_flight.keys()),
                                              return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                sid = in_flight.pop(future)
                try:
                    _, step_result, t0, t1, node_vars_log = future.result()
                except Exception as exc:  # pragma: no cover — _run_step_with_retry already catches all
                    logger.exception("[%s] DAG step raised an unexpected exception", pipeline_name)
                    step_result = StepResult(success=False, error=str(exc))
                    t0 = t1 = datetime.now(UTC)
                    node_vars_log = ''

                step = id_to_step[sid]
                duration_ms = int((t1 - t0).total_seconds() * 1000)
                result.step_results[step.name] = step_result
                result.steps_run += 1
                completed_step_entry[sid] = _step_output_entry(step_result)
                completed_vars[sid] = _step_output_vars(pipeline_name, step.name, step_result)
                _write_step_run(run_record, step, step.db_step_order, step_result, t0, t1, duration_ms, node_vars_log)
                pending.discard(sid)

                if not step_result.success:
                    result.steps_failed += 1
                    result.success = False
                    context['_pipeline_has_failed'] = True
                    if step.on_error == 'stop':
                        logger.error(
                            "[%s] DAG step '%s' failed (on_error=stop) — skipping its descendants.",
                            pipeline_name, step.name,
                        )
                        if not result.error:
                            result.error = step_result.error
                            result.error_step = step.name
                        new_skips = descendants_of[sid] - skip_ids
                        skip_ids |= new_skips
                        for skip_id in sorted(new_skips, key=lambda i: id_to_step[i].db_step_order):
                            if skip_id in pending:
                                _finalize_skip(skip_id)
                        continue  # no direct-children decrement — they're all in new_skips already
                    logger.warning("[%s] DAG step '%s' failed (on_error=continue).", pipeline_name, step.name)
                    if not result.error:
                        result.error = step_result.error

                for down in adjacency.get(sid, []):
                    if down in pending:
                        in_degree[down] -= 1
                        if in_degree[down] == 0:
                            ready.append(down)
