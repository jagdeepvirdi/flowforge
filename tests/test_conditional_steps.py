"""Tests for conditional step execution (`run_if`) in both engines. Mock steps — no DB."""
from unittest.mock import patch

import pytest
from jinja2 import UndefinedError

from flowforge.engine.context import evaluate_condition, validate_condition
from flowforge.engine.dag import run_dag
from flowforge.engine.step_exec import PipelineResult
from flowforge.steps.base import BaseStep, StepResult

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_step(name, rows=0, run_if=None, success=True, on_error='stop', order=0, step_id=None,
              parallel_group=None, ran=None):
    """A step that records that it ran and returns `rows` as rows_affected."""
    cfg = {'on_error': on_error, '_db_step_order': order}
    if run_if is not None:
        cfg['run_if'] = run_if
    if step_id:
        cfg['_db_step_id'] = step_id
    if parallel_group:
        cfg['parallel_group'] = parallel_group

    class MockStep(BaseStep):
        def run(self, context):
            if ran is not None:
                ran.append(self.name)
            return StepResult(success=success, rows_affected=rows,
                              error='' if success else 'boom')

    return MockStep(name=name, config=cfg)


def run_waves(steps, pipeline_vars=None):
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.waves._write_step_run') as write, \
         patch('flowforge.engine.runner._finish_run_record'):
        result = run_pipeline('Test Pipeline', steps, pipeline_vars=pipeline_vars)
    return result, write


def run_dag_steps(steps, edges):
    result = PipelineResult(success=True, pipeline_name='Test Pipeline')
    context = {'steps': {}, '_pipeline_has_failed': False}
    with patch('flowforge.engine.dag._write_step_run') as write:
        run_dag(steps, edges, context, result, run_record=None,
                pipeline_name='Test Pipeline', vars_log='')
    return result, write, context


def written_status(write, step_name):
    """True if _write_step_run was told to record `step_name` as skipped."""
    for call in write.call_args_list:
        step, step_result = call.args[1], call.args[3]
        if step.name == step_name:
            return step_result.skipped or call.kwargs.get('skipped', False)
    raise AssertionError(f'no step_run written for {step_name}')


# ── Expression evaluation ─────────────────────────────────────────────────────


def test_evaluate_condition_true_and_false():
    ctx = {'steps': {'q': {'rows_affected': 5}}}
    assert evaluate_condition('steps.q.rows_affected > 0', ctx) is True
    assert evaluate_condition('steps.q.rows_affected > 10', ctx) is False


def test_evaluate_condition_uses_top_level_variables_and_filters():
    ctx = {'threshold': '100', 'steps': {'q': {'rows': [{'mismatches': '150'}]}}}
    assert evaluate_condition('steps.q.rows[0].mismatches|int > threshold|int', ctx) is True
    assert evaluate_condition('steps.q.rows|length == 0', ctx) is False


def test_evaluate_condition_missing_step_raises_instead_of_silently_skipping():
    with pytest.raises(UndefinedError):
        evaluate_condition('steps.typo.rows_affected > 0', {'steps': {}})


def test_evaluate_condition_rejects_secret_variable():
    ctx = {'api_token': 'x', '_secret_var_keys': {'api_token'}, 'steps': {}}
    with pytest.raises(ValueError, match='secret'):
        evaluate_condition("api_token == 'x'", ctx)


def test_evaluate_condition_is_sandboxed():
    with pytest.raises(Exception):  # noqa: B017 — any SecurityError/UndefinedError is fine
        evaluate_condition("''.__class__.__mro__[1].__subclasses__()", {})


def test_validate_condition():
    assert validate_condition('steps.q.rows_affected > 0') is None
    assert 'valid expression' in validate_condition('steps.q.rows_affected >')
    assert 'exceeds' in validate_condition('1 == 1 ' * 200)
    assert validate_condition(5) == 'run_if must be a string'


# ── Wave engine: sequential ───────────────────────────────────────────────────


def test_wave_step_skipped_when_condition_false():
    ran = []
    steps = [make_step('check', rows=0, ran=ran),
             make_step('alert', run_if='steps.check.rows_affected > 0', ran=ran)]
    result, write = run_waves(steps)
    assert ran == ['check']
    assert result.success is True
    assert result.steps_run == 1
    assert result.step_results['alert'].skipped is True
    assert written_status(write, 'alert') is True


def test_wave_step_runs_when_condition_true():
    ran = []
    steps = [make_step('check', rows=3, ran=ran),
             make_step('alert', run_if='steps.check.rows_affected > 0', ran=ran)]
    result, _ = run_waves(steps)
    assert ran == ['check', 'alert']
    assert result.steps_run == 2
    assert result.step_results['alert'].skipped is False


def test_wave_no_condition_is_unchanged():
    ran = []
    result, _ = run_waves([make_step('a', ran=ran), make_step('b', run_if='', ran=ran)])
    assert ran == ['a', 'b']
    assert result.steps_run == 2


def test_wave_skipped_step_exposed_to_later_conditions():
    ran = []
    steps = [make_step('check', rows=0, ran=ran),
             make_step('alert', run_if='steps.check.rows_affected > 0', ran=ran),
             make_step('fallback', run_if='steps.alert.skipped', ran=ran)]
    result, _ = run_waves(steps)
    assert ran == ['check', 'fallback']
    assert result.steps_run == 2


def test_wave_condition_error_fails_step_and_stops_pipeline():
    ran = []
    steps = [make_step('alert', run_if='steps.typo.rows_affected > 0', ran=ran),
             make_step('after', ran=ran)]
    result, _ = run_waves(steps)
    assert ran == []
    assert result.success is False
    assert result.error_step == 'alert'
    assert 'run_if could not be evaluated' in result.error


def test_wave_condition_error_continues_when_on_error_continue():
    ran = []
    steps = [make_step('alert', run_if='steps.typo.x > 0', on_error='continue', ran=ran),
             make_step('after', ran=ran)]
    result, _ = run_waves(steps)
    assert ran == ['after']
    assert result.success is False
    assert result.steps_failed == 1


def test_wave_condition_can_use_pipeline_variable():
    ran = []
    steps = [make_step('send', run_if="mode == 'prod'", ran=ran)]
    run_waves(steps, pipeline_vars={'mode': 'dev'})
    assert ran == []
    run_waves(steps, pipeline_vars={'mode': 'prod'})
    assert ran == ['send']


# ── Wave engine: parallel ─────────────────────────────────────────────────────


def test_parallel_wave_skips_only_false_branch():
    ran = []
    steps = [make_step('check', rows=0, ran=ran),
             make_step('p1', parallel_group='g', run_if='steps.check.rows_affected > 0', ran=ran),
             make_step('p2', parallel_group='g', ran=ran)]
    result, write = run_waves(steps)
    assert sorted(ran) == ['check', 'p2']
    assert result.success is True
    assert result.steps_run == 2
    assert result.step_results['p1'].skipped is True
    assert written_status(write, 'p1') is True


def test_parallel_wave_condition_error_respects_on_error():
    ran = []
    steps = [make_step('p1', parallel_group='g', run_if='steps.typo.x > 0', ran=ran),
             make_step('p2', parallel_group='g', ran=ran)]
    result, _ = run_waves(steps)
    assert ran == ['p2']
    assert result.success is False
    assert result.error_step == 'p1'


# ── DAG engine ────────────────────────────────────────────────────────────────


def test_dag_step_skipped_when_condition_false():
    ran = []
    a = make_step('check', rows=0, order=1, step_id='s1', ran=ran)
    b = make_step('alert', run_if='steps.check.rows_affected > 0', order=2, step_id='s2', ran=ran)
    result, write, _ = run_dag_steps([a, b], [('s1', 's2')])
    assert ran == ['check']
    assert result.success is True
    assert result.steps_run == 1
    assert result.step_results['alert'].skipped is True
    assert written_status(write, 'alert') is True


def test_dag_step_runs_when_condition_true():
    ran = []
    a = make_step('check', rows=2, order=1, step_id='s1', ran=ran)
    b = make_step('alert', run_if='steps.check.rows_affected > 0', order=2, step_id='s2', ran=ran)
    result, _, _ = run_dag_steps([a, b], [('s1', 's2')])
    assert ran == ['check', 'alert']
    assert result.steps_run == 2


def test_dag_skipped_step_satisfies_dependents():
    """A condition-skipped step does not block or skip its descendants (skip-and-satisfy)."""
    ran = []
    a = make_step('check', rows=0, order=1, step_id='s1', ran=ran)
    b = make_step('alert', run_if='steps.check.rows_affected > 0', order=2, step_id='s2', ran=ran)
    c = make_step('cleanup', order=3, step_id='s3', ran=ran)
    result, _, _ = run_dag_steps([a, b, c], [('s1', 's2'), ('s2', 's3')])
    assert ran == ['check', 'cleanup']
    assert result.success is True
    assert result.steps_run == 2


def test_dag_descendant_can_gate_on_skipped_ancestor():
    ran = []
    a = make_step('check', rows=0, order=1, step_id='s1', ran=ran)
    b = make_step('alert', run_if='steps.check.rows_affected > 0', order=2, step_id='s2', ran=ran)
    c = make_step('all_clear', run_if='steps.alert.skipped', order=3, step_id='s3', ran=ran)
    result, _, _ = run_dag_steps([a, b, c], [('s1', 's2'), ('s2', 's3')])
    assert ran == ['check', 'all_clear']
    assert result.steps_run == 2


def test_dag_condition_only_sees_ancestors():
    """A condition referencing a non-ancestor step is undefined -> step fails, not silently skipped."""
    ran = []
    a = make_step('a', rows=5, order=1, step_id='s1', ran=ran)
    b = make_step('b', run_if='steps.a.rows_affected > 0', order=2, step_id='s2', ran=ran)
    result, _, _ = run_dag_steps([a, b], [])  # no edge: b is independent of a
    assert 'a' in ran
    assert 'b' not in ran
    assert result.success is False
    assert result.error_step == 'b'


def test_dag_condition_error_skips_descendants_with_on_error_stop():
    ran = []
    a = make_step('alert', run_if='steps.typo.x > 0', order=1, step_id='s1', ran=ran)
    b = make_step('after', order=2, step_id='s2', ran=ran)
    result, _, _ = run_dag_steps([a, b], [('s1', 's2')])
    assert ran == []
    assert result.success is False
    assert result.error_step == 'alert'


# ── Save-time validation ──────────────────────────────────────────────────────


def test_validate_pipeline_rejects_malformed_run_if():
    from flowforge.api.validators import validate_pipeline
    ok = {'name': 'p', 'steps': [{'name': 'a', 'config': {'run_if': 'steps.q.rows_affected > 0'}}]}
    bad = {'name': 'p', 'steps': [{'name': 'a', 'config': {'run_if': 'steps.q.rows_affected >'}}]}
    assert validate_pipeline(ok) is None
    assert "Step 'a'" in validate_pipeline(bad)
    assert validate_pipeline({'name': 'p', 'steps': [{'name': 'a', 'config': {'run_if': ''}}]}) is None
