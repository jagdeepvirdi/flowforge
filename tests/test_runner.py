"""Tests for the pipeline runner (engine/runner.py). Uses mock steps — no DB."""
import pytest
from unittest.mock import MagicMock, patch
from flowforge.steps.base import BaseStep, StepResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_step(name, success=True, output_path='', drive_url='', rows=0,
              on_error='stop', error_msg='step failed'):
    """Create a concrete BaseStep subclass with a predictable result."""
    result = StepResult(
        success=success,
        output_path=output_path,
        drive_url=drive_url,
        rows_affected=rows,
        error='' if success else error_msg,
    )

    class MockStep(BaseStep):
        def run(self, context):
            return result

    step = MockStep(name=name, config={'on_error': on_error})
    return step


def run(steps, pipeline_vars=None):
    from flowforge.engine.runner import run_pipeline
    # Patch DB helpers so tests work without a Flask app context
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        return run_pipeline('Test Pipeline', steps, pipeline_vars=pipeline_vars)


# ── Basic execution ───────────────────────────────────────────────────────────

def test_all_steps_run_on_success():
    steps = [make_step('a'), make_step('b'), make_step('c')]
    result = run(steps)
    assert result.success is True
    assert result.steps_run == 3
    assert result.steps_failed == 0


def test_single_step_success():
    result = run([make_step('only')])
    assert result.success is True
    assert 'only' in result.step_results


def test_empty_pipeline_succeeds():
    result = run([])
    assert result.success is True
    assert result.steps_run == 0


# ── on_error = stop ───────────────────────────────────────────────────────────

def test_on_error_stop_halts_pipeline():
    steps = [make_step('a'), make_step('b', success=False, on_error='stop'), make_step('c')]
    result = run(steps)
    assert result.success is False
    assert result.steps_run == 2          # c was never reached
    assert 'c' not in result.step_results
    assert result.error == 'step failed'


def test_on_error_stop_first_step():
    steps = [make_step('a', success=False, on_error='stop'), make_step('b'), make_step('c')]
    result = run(steps)
    assert result.success is False
    assert result.steps_run == 1
    assert result.steps_failed == 1


# ── on_error = continue ───────────────────────────────────────────────────────

def test_on_error_continue_runs_all_steps():
    steps = [make_step('a'), make_step('b', success=False, on_error='continue'), make_step('c')]
    result = run(steps)
    assert result.steps_run == 3
    assert result.steps_failed == 1
    assert 'c' in result.step_results


def test_on_error_continue_pipeline_still_fails():
    """Pipeline result is False if any step failed, even with continue."""
    steps = [make_step('a', success=False, on_error='continue')]
    result = run(steps)
    assert result.steps_failed == 1


def test_multiple_failures_with_continue():
    steps = [
        make_step('a', success=False, on_error='continue'),
        make_step('b', success=False, on_error='continue'),
        make_step('c'),
    ]
    result = run(steps)
    assert result.steps_run == 3
    assert result.steps_failed == 2
    assert result.step_results['c'].success is True


# ── Context threading ─────────────────────────────────────────────────────────

def test_step_output_available_to_next_step():
    """output_path from step A must be in context when step B runs."""
    received_context = {}

    class ProducerStep(BaseStep):
        def run(self, ctx):
            return StepResult(success=True, output_path='/tmp/report.xlsx')

    class ConsumerStep(BaseStep):
        def run(self, ctx):
            received_context.update(ctx)
            return StepResult(success=True)

    steps = [
        ProducerStep('producer', {'on_error': 'stop'}),
        ConsumerStep('consumer', {'on_error': 'stop'}),
    ]
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', steps)

    assert received_context['steps']['producer']['output_path'] == '/tmp/report.xlsx'


def test_drive_url_threaded_to_context():
    class DriveStep(BaseStep):
        def run(self, ctx):
            return StepResult(success=True, drive_url='https://drive.google.com/abc')

    received = {}

    class NextStep(BaseStep):
        def run(self, ctx):
            received.update(ctx)
            return StepResult(success=True)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', [DriveStep('uploader', {'on_error': 'stop'}),
                               NextStep('mailer', {'on_error': 'stop'})])

    assert received['steps']['uploader']['drive_url'] == 'https://drive.google.com/abc'


# ── Pipeline variables ────────────────────────────────────────────────────────

def test_pipeline_vars_in_context():
    received = {}

    class VarStep(BaseStep):
        def run(self, ctx):
            received.update(ctx)
            return StepResult(success=True)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', [VarStep('v', {'on_error': 'stop'})],
                     pipeline_vars={'region': 'APAC', 'period': '2026-05'})

    assert received['region'] == 'APAC'
    assert received['period'] == '2026-05'


# ── Result tracking ───────────────────────────────────────────────────────────

def test_step_results_keyed_by_name():
    result = run([make_step('alpha', output_path='/out.csv'), make_step('beta')])
    assert 'alpha' in result.step_results
    assert result.step_results['alpha'].output_path == '/out.csv'


def test_pipeline_name_in_result():
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        result = run_pipeline('My Report Pipeline', [make_step('x')])
    assert result.pipeline_name == 'My Report Pipeline'
