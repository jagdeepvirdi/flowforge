"""Tests for AiAnalyzeStep and its helper functions."""
import os
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flowforge.steps.ai_analyze import AiAnalyzeStep, _format_data


# ── _format_data helper ───────────────────────────────────────────────────────

def test_format_data_basic():
    cols = ['month', 'revenue']
    rows = [('2026-01', 100), ('2026-02', 120)]
    result = _format_data(cols, rows)
    assert 'month | revenue' in result
    assert '2026-01 | 100' in result
    assert '2026-02 | 120' in result


def test_format_data_empty_rows():
    assert _format_data(['col'], []) == '(no rows returned)'


def test_format_data_no_columns():
    assert _format_data([], [('x',)]) == '(no rows returned)'


def test_format_data_separator_line():
    cols = ['a', 'b']
    rows = [('1', '2')]
    lines = _format_data(cols, rows).splitlines()
    # Line 0: header, line 1: separator of dashes, line 2+: data
    assert set(lines[1]) <= set('-'), f"Expected separator line of dashes, got: {lines[1]}"


# ── Step: missing query ───────────────────────────────────────────────────────

def test_step_missing_query_returns_error():
    step = AiAnalyzeStep(name='analyze', config={})
    result = step.run({'steps': {}})
    assert not result.success
    assert 'query' in result.error


def test_step_empty_query_returns_error():
    step = AiAnalyzeStep(name='analyze', config={'query': '   '})
    result = step.run({'steps': {}})
    assert not result.success


# ── Step: query fails ─────────────────────────────────────────────────────────

def test_step_query_failure_returns_error():
    step = AiAnalyzeStep(
        name='analyze',
        config={'query': 'SELECT 1', 'connection_id': ''},
    )
    with patch.object(step, '_execute_query', side_effect=Exception('DB unavailable')):
        result = step.run({'steps': {}})
    assert not result.success
    assert 'Query failed' in result.error
    assert 'DB unavailable' in result.error


# ── Step: Ollama happy path ───────────────────────────────────────────────────

def _make_step(query='SELECT month, revenue FROM sales', prompt='Summarise.', **kwargs):
    cfg = {'query': query, 'prompt': prompt}
    cfg.update(kwargs)
    return AiAnalyzeStep(name='analyze', config=cfg)


def _mock_connection(rows, columns):
    mock_conn = MagicMock()
    mock_conn.execute_query_with_columns.return_value = (rows, columns)
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn


def test_step_ollama_happy_path():
    rows = [('2026-01', 100), ('2026-02', 120)]
    cols = ['month', 'revenue']
    step = _make_step(provider='ollama')

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Revenue rose 20% MoM.') as mock_llm:
        result = step.run({'steps': {}})

    assert result.success
    assert result.ai_summary == 'Revenue rose 20% MoM.'
    assert result.output_variables == {'ai_summary': 'Revenue rose 20% MoM.'}
    assert result.rows_affected == 2
    mock_llm.assert_called_once()


def test_step_ollama_prompt_contains_data():
    """The full prompt sent to Ollama must include the formatted data table."""
    rows = [('Jan', 500)]
    cols = ['month', 'sales']
    step = _make_step(provider='ollama', prompt='What is the trend?')

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Stable.') as mock_llm:
        step.run({'steps': {}})

    prompt_arg = mock_llm.call_args[0][0]
    assert 'month | sales' in prompt_arg
    assert 'Jan | 500' in prompt_arg
    assert 'What is the trend?' in prompt_arg


# ── Step: output_variable ─────────────────────────────────────────────────────

def test_step_default_output_variable_is_ai_summary():
    rows = [('x', 1)]
    cols = ['label', 'value']
    step = _make_step()
    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Summary text.'):
        result = step.run({'steps': {}})
    assert 'ai_summary' in result.output_variables


def test_step_custom_output_variable():
    rows = [('x', 1)]
    cols = ['label', 'value']
    step = _make_step(output_variable='revenue_summary')
    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Custom summary.'):
        result = step.run({'steps': {}})
    assert 'revenue_summary' in result.output_variables
    assert result.output_variables['revenue_summary'] == 'Custom summary.'


def test_step_output_variable_blank_falls_back_to_ai_summary():
    rows = [('x', 1)]
    cols = ['label', 'value']
    step = _make_step(output_variable='')
    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Summary.'):
        result = step.run({'steps': {}})
    assert 'ai_summary' in result.output_variables


# ── Step: max_rows truncation ─────────────────────────────────────────────────

def test_step_max_rows_truncates_data():
    """max_rows=3 means only 3 rows are sent to LLM even if query returns more."""
    rows = [(f'row{i}', i) for i in range(10)]
    cols = ['label', 'value']
    step = _make_step(max_rows=3)

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='OK.') as mock_llm:
        result = step.run({'steps': {}})

    prompt_arg = mock_llm.call_args[0][0]
    # rows_affected shows total; prompt mentions truncation
    assert result.rows_affected == 10
    assert 'Showing first 3 of 10 rows' in prompt_arg


def test_step_max_rows_hard_cap_enforced():
    """max_rows cannot exceed _MAX_ROWS_HARD_CAP (500), even if configured higher."""
    from flowforge.steps.ai_analyze import _MAX_ROWS_HARD_CAP
    rows = [(f'r{i}', i) for i in range(_MAX_ROWS_HARD_CAP + 50)]
    cols = ['a', 'b']
    step = _make_step(max_rows=_MAX_ROWS_HARD_CAP + 200)

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Ok.') as mock_llm:
        step.run({'steps': {}})

    prompt_arg = mock_llm.call_args[0][0]
    assert f'Showing first {_MAX_ROWS_HARD_CAP}' in prompt_arg


def test_step_no_truncation_note_when_rows_within_limit():
    rows = [('a', 1), ('b', 2)]
    cols = ['label', 'v']
    step = _make_step(max_rows=100)

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Fine.') as mock_llm:
        step.run({'steps': {}})

    prompt_arg = mock_llm.call_args[0][0]
    assert 'Showing first' not in prompt_arg


# ── Step: Ollama unreachable ──────────────────────────────────────────────────

def test_step_ollama_unreachable_returns_failure():
    rows = [('x', 1)]
    cols = ['a', 'b']
    step = _make_step(provider='ollama')

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama',
               side_effect=urllib.error.URLError('connection refused')):
        result = step.run({'steps': {}})

    assert not result.success
    assert 'Ollama' in result.error


# ── Step: Claude provider ─────────────────────────────────────────────────────

def test_step_claude_happy_path():
    rows = [('Q1', 50000)]
    cols = ['quarter', 'revenue']
    step = _make_step(provider='claude')

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_claude', return_value='Q1 revenue was 50K.') as mock_claude:
        result = step.run({'steps': {}})

    assert result.success
    assert result.ai_summary == 'Q1 revenue was 50K.'
    mock_claude.assert_called_once()


def test_step_claude_uses_configured_model():
    rows = [('x', 1)]
    cols = ['a', 'b']
    step = _make_step(provider='claude', model='claude-opus-4-7')

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_claude', return_value='Text.') as mock_claude:
        step.run({'steps': {}})

    model_arg = mock_claude.call_args[0][1]
    assert model_arg == 'claude-opus-4-7'


def test_step_claude_missing_api_key_returns_failure():
    rows = [('x', 1)]
    cols = ['a', 'b']
    step = _make_step(provider='claude')

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_claude',
               side_effect=ValueError('ANTHROPIC_API_KEY is not set')):
        result = step.run({'steps': {}})

    assert not result.success
    assert 'ANTHROPIC_API_KEY' in result.error


def test_step_claude_not_installed_returns_failure():
    rows = [('x', 1)]
    cols = ['a', 'b']
    step = _make_step(provider='claude')

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_claude',
               side_effect=ImportError('pip install anthropic')):
        result = step.run({'steps': {}})

    assert not result.success
    assert 'pip install' in result.error


# ── Step: Jinja2 variable rendering in query and prompt ──────────────────────

def test_step_renders_jinja_in_query():
    """SQL query should resolve {{ current_month }} before execution."""
    from flowforge.engine.context import build
    ctx = build('test')
    step = _make_step(query="SELECT * FROM sales WHERE month = '{{ current_month }}'")

    captured_sql = []

    def fake_execute(conn_id, sql):
        captured_sql.append(sql)
        return ([('x', 1)], ['a', 'b'])

    with patch.object(step, '_execute_query', side_effect=fake_execute), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='ok'):
        step.run(ctx)

    assert '{{' not in captured_sql[0], "Jinja2 variables were not rendered in query"
    assert ctx['current_month'] in captured_sql[0]


def test_step_renders_jinja_in_prompt():
    """Prompt should resolve {{ pipeline_name }} before being sent to LLM."""
    from flowforge.engine.context import build
    ctx = build('Revenue Pipeline')
    step = _make_step(query='SELECT 1', prompt='Summarise data for {{ pipeline_name }}.')

    with patch.object(step, '_execute_query', return_value=([('x',)], ['col'])), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='ok') as mock_llm:
        step.run(ctx)

    prompt_arg = mock_llm.call_args[0][0]
    assert 'Revenue Pipeline' in prompt_arg
    assert '{{' not in prompt_arg


# ── Step: result exposed in runner context ────────────────────────────────────

def test_step_result_exposes_ai_summary_field():
    """StepResult.ai_summary must be set so runner can expose it to step context."""
    rows = [('x', 1)]
    cols = ['a', 'b']
    step = _make_step()

    with patch.object(step, '_execute_query', return_value=(rows, cols)), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='My summary.'):
        result = step.run({'steps': {}})

    assert result.ai_summary == 'My summary.'


def _run_no_db(steps):
    """Run a pipeline without a Flask app context by patching DB helpers."""
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('flowforge.engine.runner.audit'):
        return run_pipeline('test', steps)


def test_runner_exposes_ai_summary_to_step_context():
    """Runner must include ai_summary in context['steps'][<name>]."""
    step = _make_step()

    with patch.object(step, '_execute_query', return_value=([('x', 1)], ['a', 'b'])), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Injected summary.'):
        pipeline_result = _run_no_db([step])

    step_ctx = pipeline_result.step_results['analyze']
    assert step_ctx.ai_summary == 'Injected summary.'


def test_runner_injects_output_variable_into_top_level_context():
    """output_variables from ai_analyze must reach top-level context for downstream steps."""
    from flowforge.steps.base import BaseStep, StepResult

    captured_context: dict = {}

    class CapturingStep(BaseStep):
        step_type = 'capture'
        def run(self, context):
            captured_context.update(context)
            return StepResult(success=True)

    ai_step = _make_step(output_variable='monthly_summary')
    capture  = CapturingStep(name='capture', config={})

    with patch.object(ai_step, '_execute_query', return_value=([('x', 1)], ['a', 'b'])), \
         patch('flowforge.steps.ai_analyze._call_ollama', return_value='Top-level text.'):
        _run_no_db([ai_step, capture])

    assert captured_context.get('monthly_summary') == 'Top-level text.'


# ── Step: step_type attribute ─────────────────────────────────────────────────

def test_step_type_attribute():
    step = AiAnalyzeStep(name='s', config={'query': 'SELECT 1'})
    assert step.step_type == 'ai_analyze'


# ── Loader: ai_analyze is registered ─────────────────────────────────────────

def test_loader_registers_ai_analyze():
    from flowforge.engine.loader import _STEP_CLASSES
    assert 'ai_analyze' in _STEP_CLASSES
    assert 'AiAnalyzeStep' in _STEP_CLASSES['ai_analyze']
