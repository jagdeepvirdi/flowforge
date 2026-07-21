"""Tests for flowforge/engine/dag.py — the topological DAG execution engine
(Phase 14 Option B, Milestone 2). Unit-level: exercises `run_dag` directly against
in-memory BaseStep fixtures, with `_write_step_run` mocked out (no DB required).
"""
import time
from unittest.mock import patch

from flowforge.engine.dag import run_dag
from flowforge.engine.runner import PipelineResult
from flowforge.steps.base import BaseStep, StepResult


def make_dag_step(name, step_id, step_order, on_error='stop', run_fn=None,
                  success=True, error_msg='step failed', output_variables=None):
    if run_fn is None:
        result = StepResult(success=success, error='' if success else error_msg,
                            output_variables=output_variables or {})

        def run_fn(ctx):
            return result

    class MockStep(BaseStep):
        def run(self, ctx):
            return run_fn(ctx)

    cfg = {'on_error': on_error, '_db_step_order': step_order, '_db_step_id': step_id}
    return MockStep(name=name, config=cfg)


def run(steps, edges):
    """Run the DAG with _write_step_run mocked out; returns (result, mock_write)."""
    result = PipelineResult(success=True, pipeline_name='Test Pipeline')
    context = {'steps': {}, '_pipeline_has_failed': False}
    with patch('flowforge.engine.dag._write_step_run') as mock_write:
        run_dag(steps, edges, context, result, run_record=None,
               pipeline_name='Test Pipeline', vars_log='VARS_DUMP')
    return result, mock_write, context


# ── basic execution ───────────────────────────────────────────────────────────

def test_linear_chain_all_succeed():
    a = make_dag_step('a', 's1', 1)
    b = make_dag_step('b', 's2', 2)
    c = make_dag_step('c', 's3', 3)
    result, _, _ = run([a, b, c], [('s1', 's2'), ('s2', 's3')])
    assert result.success is True
    assert result.steps_run == 3
    assert result.steps_failed == 0


def test_no_edges_all_independent_steps_run():
    steps = [make_dag_step(n, f's{i}', i) for i, n in enumerate(['a', 'b', 'c'], start=1)]
    result, _, _ = run(steps, [])
    assert result.success is True
    assert result.steps_run == 3


def test_independent_branches_run_concurrently():
    """Three independent steps that each sleep 0.2s should finish well under 0.6s combined."""
    def make_sleepy(name, step_id, order):
        def run_fn(ctx):
            time.sleep(0.2)
            return StepResult(success=True)
        return make_dag_step(name, step_id, order, run_fn=run_fn)

    steps = [make_sleepy(n, f's{i}', i) for i, n in enumerate(['a', 'b', 'c'], start=1)]
    t0 = time.monotonic()
    result, _, _ = run(steps, [])
    elapsed = time.monotonic() - t0
    assert result.success is True
    assert elapsed < 0.5


# ── branch-scoped on_error=stop ───────────────────────────────────────────────

def test_stop_failure_skips_only_descendants():
    """A (stop, fails) -> B; independent C has no relation to A and must still run."""
    a = make_dag_step('a', 's1', 1, on_error='stop', success=False, error_msg='boom')
    b = make_dag_step('b', 's2', 2)
    c = make_dag_step('c', 's3', 3)
    result, mock_write, _ = run([a, b, c], [('s1', 's2')])

    assert result.success is False
    assert result.error_step == 'a'
    assert 'boom' in result.error

    assert result.step_results['b'].success is False
    assert 'Skipped' in result.step_results['b'].error
    assert result.step_results['c'].success is True

    # b was written with skipped=True; c was written normally
    skip_calls = [c for c in mock_write.call_args_list if c.kwargs.get('skipped')]
    assert len(skip_calls) == 1
    assert skip_calls[0].args[1].name == 'b'


def test_stop_failure_skips_transitive_descendants_multi_level():
    """A (stop, fails) -> B -> C: both B and C must be skipped."""
    a = make_dag_step('a', 's1', 1, on_error='stop', success=False)
    b = make_dag_step('b', 's2', 2)
    c = make_dag_step('c', 's3', 3)
    result, _, _ = run([a, b, c], [('s1', 's2'), ('s2', 's3')])

    assert result.steps_run == 1  # only 'a' actually ran
    assert 'Skipped' in result.step_results['b'].error
    assert 'Skipped' in result.step_results['c'].error


def test_continue_failure_lets_children_run():
    """A (continue, fails) -> B: B should still run, unlike the stop case."""
    a = make_dag_step('a', 's1', 1, on_error='continue', success=False, error_msg='minor')
    b = make_dag_step('b', 's2', 2)
    result, _, _ = run([a, b], [('s1', 's2')])

    assert result.success is False  # any failure marks the run failed, regardless of on_error
    assert result.step_results['b'].success is True
    assert 'Skipped' not in (result.step_results['b'].error or '')


def test_merge_point_downstream_of_stop_failure_is_skipped_even_with_independent_upstream():
    """D depends on both A (fails, stop) and C (independent, succeeds) -> D must be skipped."""
    a = make_dag_step('a', 's1', 1, on_error='stop', success=False)
    c = make_dag_step('c', 's3', 2)
    d = make_dag_step('d', 's4', 3)
    result, _, _ = run([a, c, d], [('s1', 's4'), ('s3', 's4')])

    assert result.step_results['c'].success is True
    assert 'Skipped' in result.step_results['d'].error


# ── ancestors-only context visibility ─────────────────────────────────────────

def test_context_only_exposes_transitive_ancestors():
    """C depends on A only; B is independent. C's context must see A's output, not B's."""
    seen = {}

    a = make_dag_step('a', 's1', 1, output_variables={'a_var': 'from_a'})
    b = make_dag_step('b', 's2', 2, output_variables={'b_var': 'from_b'})

    def c_run(ctx):
        seen['steps_keys'] = set(ctx['steps'].keys())
        seen['a_var'] = ctx.get('a_var')
        seen['b_var'] = ctx.get('b_var')
        return StepResult(success=True)

    c = make_dag_step('c', 's3', 3, run_fn=c_run)
    run([a, b, c], [('s1', 's3')])

    assert seen['steps_keys'] == {'a'}
    assert seen['a_var'] == 'from_a'
    assert seen['b_var'] is None


def test_context_step_output_entry_visible_to_descendant():
    a = make_dag_step('a', 's1', 1, success=True)
    seen = {}

    def b_run(ctx):
        seen['a_entry'] = ctx['steps'].get('a')
        return StepResult(success=True)

    b = make_dag_step('b', 's2', 2, run_fn=b_run)
    run([a, b], [('s1', 's2')])

    assert seen['a_entry'] is not None
    assert seen['a_entry']['rows_affected'] == 0


# ── disabled/missing step edges ────────────────────────────────────────────────

def test_edge_referencing_missing_step_is_dropped_not_fatal():
    a = make_dag_step('a', 's1', 1)
    b = make_dag_step('b', 's2', 2)
    # 's999' doesn't correspond to any loaded step (e.g. disabled) — must not raise or hang.
    result, _, _ = run([a, b], [('s999', 's2'), ('s1', 's999')])
    assert result.success is True
    assert result.steps_run == 2


# ── vars_log placement ────────────────────────────────────────────────────────

def test_vars_log_attached_to_first_root_only():
    a = make_dag_step('a', 's1', 1)
    b = make_dag_step('b', 's2', 2)
    _, mock_write, _ = run([a, b], [])

    vars_log_calls = [c.args[7] for c in mock_write.call_args_list]
    assert vars_log_calls.count('VARS_DUMP') == 1
    # the lowest db_step_order root gets it
    first_call = next(c for c in mock_write.call_args_list if c.args[7] == 'VARS_DUMP')
    assert first_call.args[1].name == 'a'


# ── pipeline_has_failed flag ───────────────────────────────────────────────────

def test_pipeline_has_failed_flag_set_on_context():
    a = make_dag_step('a', 's1', 1, success=False, error_msg='x')
    _, _, context = run([a], [])
    assert context['_pipeline_has_failed'] is True
