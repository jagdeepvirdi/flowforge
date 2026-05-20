"""Tests that invalid Jinja2 templates in step config fail gracefully (TEST-3b).

The runner catches any exception from step.run() and returns StepResult(success=False).
This verifies the pipeline doesn't crash on bad template strings.
"""
import pytest
from unittest.mock import patch
from flowforge.steps.base import BaseStep, StepResult
from flowforge.engine.runner import run_pipeline


def _run(steps):
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        return run_pipeline('Jinja Error Test', steps)


class BadTemplateStep(BaseStep):
    """Step that tries to render an invalid Jinja2 template."""
    step_type = 'db_query'

    def run(self, context):
        from flowforge.engine.context import render
        render(self.config.get('template', ''), context)
        return StepResult(success=True)


# ── render() itself ───────────────────────────────────────────────────────────

def test_render_raises_on_unclosed_tag():
    from jinja2 import TemplateSyntaxError
    from flowforge.engine.context import render
    with pytest.raises(TemplateSyntaxError):
        render('{{ unclosed', {})


def test_render_raises_on_bad_block():
    from jinja2 import TemplateSyntaxError
    from flowforge.engine.context import render
    with pytest.raises(TemplateSyntaxError):
        render('{% if %}missing condition{% endif %}', {})


# ── Runner catches errors and returns StepResult(success=False) ───────────────

def test_unclosed_tag_in_step_does_not_crash_runner():
    step = BadTemplateStep('bad_step', {'on_error': 'stop', 'template': '{{ unclosed'})
    result = _run([step])
    assert result.success is False
    assert result.steps_failed == 1


def test_invalid_template_step_result_has_error_message():
    step = BadTemplateStep('bad_step', {'on_error': 'stop', 'template': '{{ unclosed'})
    result = _run([step])
    assert result.step_results['bad_step'].success is False
    assert result.step_results['bad_step'].error != ''


def test_continue_on_error_after_bad_template():
    """Pipeline continues past a bad template step when on_error=continue."""

    class GoodStep(BaseStep):
        step_type = 'db_query'
        def run(self, ctx):
            return StepResult(success=True)

    steps = [
        BadTemplateStep('bad', {'on_error': 'continue', 'template': '{{ unclosed'}),
        GoodStep('good', {'on_error': 'stop'}),
    ]
    result = _run(steps)
    assert result.steps_run == 2
    assert result.steps_failed == 1
    assert result.step_results['good'].success is True


def test_valid_template_in_step_succeeds():
    step = BadTemplateStep('ok_step', {
        'on_error': 'stop',
        'template': 'Hello {{ current_date }}',
    })
    result = _run([step])
    assert result.success is True
    assert result.steps_run == 1
