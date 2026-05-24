"""Tests for AI utility endpoints (POST /api/ai/*)."""
import json
import urllib.error
from unittest.mock import patch

import pytest


# ── Default: AI always enabled within this module ────────────────────────────

@pytest.fixture(autouse=True)
def enable_ai(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AI_ENABLED', 'true')


# ── Global enable/disable toggle ──────────────────────────────────────────────

def test_ai_disabled_returns_503_chart(client, headers, monkeypatch):
    """All AI endpoints return 503 when FLOWFORGE_AI_ENABLED=false."""
    monkeypatch.setenv('FLOWFORGE_AI_ENABLED', 'false')
    resp = client.post('/api/ai/chart-config',
                       json={'columns': ['x', 'y'], 'rows': []},
                       headers=headers)
    assert resp.status_code == 503
    assert 'disabled' in resp.get_json()['error'].lower()


def test_ai_disabled_returns_503_query(client, headers, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AI_ENABLED', 'false')
    resp = client.post('/api/ai/query',
                       json={'task': 'explain', 'sql': 'SELECT 1'},
                       headers=headers)
    assert resp.status_code == 503


def test_ai_disabled_returns_503_data_profile(client, headers, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AI_ENABLED', 'false')
    resp = client.post('/api/ai/data-profile',
                       json={'columns': ['x'], 'rows': []},
                       headers=headers)
    assert resp.status_code == 503


def test_ai_disabled_returns_503_anomaly(client, headers, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AI_ENABLED', 'false')
    resp = client.post('/api/ai/anomaly-narrative',
                       json={'step_name': 'S', 'metric': 'rows', 'value': 1, 'mean': 1},
                       headers=headers)
    assert resp.status_code == 503


# ── Auth required ─────────────────────────────────────────────────────────────

def test_ai_endpoints_require_auth(client):
    """All AI endpoints return 401 without a valid token."""
    endpoints_and_payloads = [
        ('/api/ai/chart-config',       {'columns': ['x'], 'rows': []}),
        ('/api/ai/query',              {'task': 'explain', 'sql': 'SELECT 1'}),
        ('/api/ai/data-profile',       {'columns': ['x'], 'rows': []}),
        ('/api/ai/anomaly-narrative',  {'step_name': 'S', 'metric': 'rows', 'value': 1, 'mean': 1}),
    ]
    for url, payload in endpoints_and_payloads:
        resp = client.post(url, json=payload)
        assert resp.status_code == 401, f'{url} should require auth, got {resp.status_code}'


# ── POST /api/ai/chart-config ─────────────────────────────────────────────────

def test_chart_config_happy_path(client, headers):
    mock_json = json.dumps({'type': 'bar', 'x': 'month', 'y': 'revenue', 'title': 'Revenue by Month'})
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=mock_json):
        resp = client.post('/api/ai/chart-config',
                           json={'columns': ['month', 'revenue'], 'rows': [['2026-01', 100]]},
                           headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['type'] == 'bar'
    assert data['x'] == 'month'
    assert data['y'] == 'revenue'
    assert data['title'] == 'Revenue by Month'


def test_chart_config_sanitises_invalid_type(client, headers):
    """LLM response with an unknown chart type is corrected to 'bar'."""
    bad = json.dumps({'type': 'donut', 'x': 'month', 'y': 'revenue', 'title': 'T'})
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=bad):
        resp = client.post('/api/ai/chart-config',
                           json={'columns': ['month', 'revenue'], 'rows': []},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['type'] == 'bar'


def test_chart_config_sanitises_invalid_x_column(client, headers):
    """LLM response with a column not in input list is corrected to columns[0]."""
    bad = json.dumps({'type': 'line', 'x': 'unknown_col', 'y': 'revenue', 'title': 'T'})
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=bad):
        resp = client.post('/api/ai/chart-config',
                           json={'columns': ['month', 'revenue'], 'rows': []},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['x'] == 'month'


def test_chart_config_sanitises_invalid_y_column(client, headers):
    """LLM response with a bad y-column is corrected to columns[-1]."""
    bad = json.dumps({'type': 'bar', 'x': 'month', 'y': 'ghost', 'title': 'T'})
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=bad):
        resp = client.post('/api/ai/chart-config',
                           json={'columns': ['month', 'revenue'], 'rows': []},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['y'] == 'revenue'


def test_chart_config_includes_available_columns(client, headers):
    ok = json.dumps({'type': 'bar', 'x': 'month', 'y': 'revenue', 'title': 'T'})
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=ok):
        resp = client.post('/api/ai/chart-config',
                           json={'columns': ['month', 'revenue', 'region'], 'rows': []},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['available_columns'] == ['month', 'revenue', 'region']


def test_chart_config_missing_columns_returns_400(client, headers):
    resp = client.post('/api/ai/chart-config', json={}, headers=headers)
    assert resp.status_code == 400
    assert 'columns' in resp.get_json()['error']


def test_chart_config_ollama_unreachable_returns_503(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate',
               side_effect=urllib.error.URLError('connection refused')):
        resp = client.post('/api/ai/chart-config',
                           json={'columns': ['x', 'y'], 'rows': []},
                           headers=headers)
    assert resp.status_code == 503
    assert 'Ollama' in resp.get_json()['error']


def test_chart_config_bad_json_from_llm_falls_back_gracefully(client, headers):
    """Malformed JSON from Ollama results in a sanitised default response (no 500)."""
    with patch('flowforge.api.routes.ai._ollama_generate', return_value='not json at all'):
        resp = client.post('/api/ai/chart-config',
                           json={'columns': ['month', 'revenue'], 'rows': []},
                           headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['type'] == 'bar'   # sanitised default
    assert data['x'] == 'month'


# ── POST /api/ai/query — explain ─────────────────────────────────────────────

def test_query_explain_returns_text(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate',
               return_value='This query selects all active users.'):
        resp = client.post('/api/ai/query',
                           json={'task': 'explain', 'sql': 'SELECT * FROM users WHERE active'},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['result'] == 'This query selects all active users.'


def test_query_explain_missing_sql_returns_400(client, headers):
    resp = client.post('/api/ai/query', json={'task': 'explain'}, headers=headers)
    assert resp.status_code == 400
    assert 'sql' in resp.get_json()['error']


# ── POST /api/ai/query — optimize ────────────────────────────────────────────

def test_query_optimize_extracts_sql_from_json(client, headers):
    optimized_json = json.dumps({'sql': 'SELECT id FROM users WHERE active = true'})
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=optimized_json):
        resp = client.post('/api/ai/query',
                           json={'task': 'optimize', 'sql': 'SELECT * FROM users WHERE active = true'},
                           headers=headers)
    assert resp.status_code == 200
    assert 'SELECT id FROM users' in resp.get_json()['result']


def test_query_optimize_bad_json_returns_raw(client, headers):
    """Non-JSON Ollama response for optimize falls back to the raw string."""
    with patch('flowforge.api.routes.ai._ollama_generate',
               return_value='SELECT id FROM users WHERE active'):
        resp = client.post('/api/ai/query',
                           json={'task': 'optimize', 'sql': 'SELECT * FROM users'},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['result'] == 'SELECT id FROM users WHERE active'


def test_query_optimize_missing_sql_returns_400(client, headers):
    resp = client.post('/api/ai/query', json={'task': 'optimize'}, headers=headers)
    assert resp.status_code == 400


# ── POST /api/ai/query — diagnose ────────────────────────────────────────────

def test_query_diagnose_returns_narrative(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate',
               return_value='The DB connection was refused because the host is unreachable.'):
        resp = client.post('/api/ai/query',
                           json={'task': 'diagnose', 'step_type': 'db_query',
                                 'error': 'Connection refused'},
                           headers=headers)
    assert resp.status_code == 200
    assert 'result' in resp.get_json()


def test_query_diagnose_missing_error_returns_400(client, headers):
    resp = client.post('/api/ai/query',
                       json={'task': 'diagnose', 'step_type': 'db_query'},
                       headers=headers)
    assert resp.status_code == 400
    assert 'error' in resp.get_json()['error']


def test_query_diagnose_accepts_logs_field(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate', return_value='ORA-00942 fix: check table name.') as mock:
        resp = client.post('/api/ai/query',
                           json={'task': 'diagnose', 'step_type': 'db_procedure',
                                 'error': 'ORA-00942: table or view does not exist',
                                 'logs': 'Running procedure pkg.proc\nORA-00942'},
                           headers=headers)
    assert resp.status_code == 200
    # Confirm logs were included in the prompt
    call_prompt = mock.call_args[0][0]
    assert 'ORA-00942' in call_prompt


# ── POST /api/ai/query — invalid task ────────────────────────────────────────

def test_query_invalid_task_returns_400(client, headers):
    resp = client.post('/api/ai/query',
                       json={'task': 'summarize', 'sql': 'SELECT 1'},
                       headers=headers)
    assert resp.status_code == 400
    assert 'Unknown task' in resp.get_json()['error']


def test_query_empty_task_returns_400(client, headers):
    resp = client.post('/api/ai/query', json={}, headers=headers)
    assert resp.status_code == 400


def test_query_ollama_unreachable_returns_503(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate',
               side_effect=urllib.error.URLError('connection refused')):
        resp = client.post('/api/ai/query',
                           json={'task': 'explain', 'sql': 'SELECT 1'},
                           headers=headers)
    assert resp.status_code == 503
    assert 'Ollama' in resp.get_json()['error']


# ── POST /api/ai/data-profile ─────────────────────────────────────────────────

def test_data_profile_returns_narrative(client, headers):
    narrative = 'This dataset contains monthly sales data across 3 regions.'
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=narrative):
        resp = client.post('/api/ai/data-profile',
                           json={'columns': ['month', 'sales', 'region'],
                                 'rows': [['2026-01', 100, 'APAC'], ['2026-02', 120, 'EMEA']]},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['result'] == narrative


def test_data_profile_missing_columns_returns_400(client, headers):
    resp = client.post('/api/ai/data-profile', json={}, headers=headers)
    assert resp.status_code == 400
    assert 'columns' in resp.get_json()['error']


def test_data_profile_sends_at_most_20_rows(client, headers):
    """API must sample at most 20 rows regardless of how many are sent."""
    rows = [[f'2026-{i:02d}', i * 100] for i in range(1, 51)]
    with patch('flowforge.api.routes.ai._ollama_generate', return_value='Summary.') as mock:
        resp = client.post('/api/ai/data-profile',
                           json={'columns': ['month', 'sales'], 'rows': rows},
                           headers=headers)
    assert resp.status_code == 200
    prompt = mock.call_args[0][0]
    assert '20 rows' in prompt


def test_data_profile_ollama_unreachable_returns_503(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate',
               side_effect=urllib.error.URLError('no route to host')):
        resp = client.post('/api/ai/data-profile',
                           json={'columns': ['x'], 'rows': []},
                           headers=headers)
    assert resp.status_code == 503


# ── POST /api/ai/anomaly-narrative ───────────────────────────────────────────

def test_anomaly_narrative_rows_metric(client, headers):
    narrative = 'The step processed far fewer rows than its 30-run average.'
    with patch('flowforge.api.routes.ai._ollama_generate', return_value=narrative):
        resp = client.post('/api/ai/anomaly-narrative',
                           json={'step_name': 'Load Customers', 'metric': 'rows',
                                 'value': 500, 'mean': 10000, 'pct_diff': -95.0},
                           headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['result'] == narrative


def test_anomaly_narrative_duration_metric(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate',
               return_value='The step took far longer than usual; check for table locks.'):
        resp = client.post('/api/ai/anomaly-narrative',
                           json={'step_name': 'Generate Report', 'metric': 'duration',
                                 'value': 120000, 'mean': 5000, 'pct_diff': 2300.0},
                           headers=headers)
    assert resp.status_code == 200
    assert 'result' in resp.get_json()


def test_anomaly_narrative_missing_value_returns_400(client, headers):
    resp = client.post('/api/ai/anomaly-narrative',
                       json={'step_name': 'Load', 'metric': 'rows', 'mean': 1000},
                       headers=headers)
    assert resp.status_code == 400


def test_anomaly_narrative_missing_mean_returns_400(client, headers):
    resp = client.post('/api/ai/anomaly-narrative',
                       json={'step_name': 'Load', 'metric': 'rows', 'value': 500},
                       headers=headers)
    assert resp.status_code == 400


def test_anomaly_narrative_invalid_metric_returns_400(client, headers):
    """metric must be 'rows' or 'duration'."""
    resp = client.post('/api/ai/anomaly-narrative',
                       json={'step_name': 'Load', 'metric': 'cpu',
                             'value': 100, 'mean': 50},
                       headers=headers)
    assert resp.status_code == 400


def test_anomaly_narrative_missing_step_name_returns_400(client, headers):
    resp = client.post('/api/ai/anomaly-narrative',
                       json={'metric': 'rows', 'value': 100, 'mean': 1000},
                       headers=headers)
    assert resp.status_code == 400


def test_anomaly_narrative_ollama_unreachable_returns_503(client, headers):
    with patch('flowforge.api.routes.ai._ollama_generate',
               side_effect=urllib.error.URLError('timeout')):
        resp = client.post('/api/ai/anomaly-narrative',
                           json={'step_name': 'Step', 'metric': 'rows',
                                 'value': 0, 'mean': 1000, 'pct_diff': -100.0},
                           headers=headers)
    assert resp.status_code == 503
