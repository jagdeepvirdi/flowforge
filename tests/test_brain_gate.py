"""Tests for the Brain attach gate (flowforge/brain.py) and the dark AI surfaces."""
from unittest.mock import patch

import pytest

from flowforge.brain import brain_enabled, brain_unavailable_response
from flowforge.engine.context import build, render
from flowforge.engine.loader import _STEP_CLASSES, _import_step_class, get_step_types
from flowforge.engine.runner import run_pipeline
from flowforge.steps.ai_analyze import AiAnalyzeStep
from flowforge.steps.base import BaseStep, StepResult

_AI_ENDPOINTS = [
    ('/api/ai/data-profile',      {'columns': ['x'], 'rows': []}),
    ('/api/ai/chart-config',      {'columns': ['x'], 'rows': []}),
    ('/api/ai/query',             {'task': 'explain', 'sql': 'SELECT 1'}),
    ('/api/ai/anomaly-narrative', {'step_name': 'S', 'metric': 'rows', 'value': 1, 'mean': 1}),
]


# ── Gate module ──────────────────────────────────────────────────────────────

def test_brain_disabled_in_phase_a(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_BRAIN_URL', 'http://brain.example:8000')
    assert brain_enabled() is False


def test_brain_unavailable_response_shape(app):
    with app.test_request_context():
        resp, status = brain_unavailable_response()
    assert status == 503
    body = resp.get_json()
    assert body['error'] == 'brain_not_attached'
    assert 'FLOWFORGE_BRAIN_URL' in body['message']


# ── /api/ai/* shells ─────────────────────────────────────────────────────────

@pytest.mark.parametrize('url,payload', _AI_ENDPOINTS)
def test_ai_endpoints_return_brain_not_attached(client, headers, url, payload):
    resp = client.post(url, json=payload, headers=headers)
    assert resp.status_code == 503
    assert resp.get_json()['error'] == 'brain_not_attached'


@pytest.mark.parametrize('url,payload', _AI_ENDPOINTS)
def test_ai_endpoints_still_require_auth(client, url, payload):
    assert client.post(url, json=payload).status_code == 401


# ── /setup/status ────────────────────────────────────────────────────────────

def test_setup_status_ai_disabled_without_brain(client, headers, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_BRAIN_URL', raising=False)
    ai = client.get('/api/setup/status', headers=headers).get_json()['ai']
    assert ai == {'enabled': False, 'brain_url_configured': False}


def test_setup_status_reports_brain_url_configured_but_not_enabled(client, headers, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_BRAIN_URL', 'http://brain.example:8000')
    ai = client.get('/api/setup/status', headers=headers).get_json()['ai']
    assert ai == {'enabled': False, 'brain_url_configured': True}


def test_setup_status_has_no_provider_fields(client, headers):
    ai = client.get('/api/setup/status', headers=headers).get_json()['ai']
    assert set(ai) == {'enabled', 'brain_url_configured'}


# ── ai_analyze step ──────────────────────────────────────────────────────────

def test_ai_analyze_step_fails_with_clear_message():
    result = AiAnalyzeStep('analyse', {'query': 'SELECT 1'}).run({})
    assert result.success is False
    assert 'Brain service' in result.error
    assert 'FLOWFORGE_BRAIN_URL' in result.error
    assert result.output_variables == {}


def test_ai_analyze_step_type_still_registered():
    assert 'ai_analyze' in _STEP_CLASSES
    assert 'ai_analyze' in get_step_types()
    assert _import_step_class(_STEP_CLASSES['ai_analyze']) is AiAnalyzeStep
    assert AiAnalyzeStep.step_type == 'ai_analyze'


def _run(steps):
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        return run_pipeline('Brain Gate Test', steps)


class _OkStep(BaseStep):
    step_type = 'db_query'

    def run(self, context):
        return StepResult(success=True)


def test_ai_analyze_on_error_stop_halts_pipeline():
    result = _run([AiAnalyzeStep('ai', {'on_error': 'stop'}), _OkStep('after', {})])
    assert result.success is False
    assert result.steps_run == 1
    assert 'after' not in result.step_results


def test_ai_analyze_on_error_continue_runs_next_step():
    result = _run([AiAnalyzeStep('ai', {'on_error': 'continue'}), _OkStep('after', {})])
    assert result.steps_run == 2
    assert result.steps_failed == 1
    assert result.step_results['after'].success is True


# ── Secret blocklist ─────────────────────────────────────────────────────────

@pytest.mark.parametrize('name', ['FLOWFORGE_BRAIN_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY'])
def test_template_env_blocks_brain_and_legacy_provider_keys(monkeypatch, name):
    monkeypatch.setenv(name, 'secret-value')
    assert render(f'{{{{ env.{name} }}}}', build('test')) == ''
