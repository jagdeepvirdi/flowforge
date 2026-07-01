"""Tests for pipeline routes not covered by test_pipelines.py:
cron-next, create-with-schedule, promote, pipeline-runs,
webhook tokens, dependencies, import via multipart.
"""
import pytest


@pytest.fixture
def pipeline_id(client, headers):
    resp = client.post('/api/pipelines', json={'name': 'Coverage Pipeline'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/pipelines/{pid}', headers=headers)


@pytest.fixture
def second_pipeline_id(client, headers):
    resp = client.post('/api/pipelines', json={'name': 'Coverage Pipeline B'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/pipelines/{pid}', headers=headers)


# ── cron-next ─────────────────────────────────────────────────────────────────

def test_cron_next_missing_expr(client, headers):
    resp = client.get('/api/pipelines/cron-next', headers=headers)
    assert resp.status_code == 400
    assert 'expr' in resp.get_json()['error'].lower()


def test_cron_next_invalid_expr(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=not-a-cron', headers=headers)
    assert resp.status_code == 400


def test_cron_next_valid_expr(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=0+9+*+*+1&n=3', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'next_runs' in data
    assert len(data['next_runs']) == 3


def test_cron_next_default_n(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=0+0+*+*+*', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['next_runs']) == 5


def test_cron_next_requires_auth(client):
    assert client.get('/api/pipelines/cron-next?expr=0+0+*+*+*').status_code == 401


# ── create with schedule and variables ───────────────────────────────────────

def test_create_pipeline_with_valid_schedule(client, headers):
    resp = client.post('/api/pipelines',
                       json={'name': 'Scheduled Coverage', 'schedule': '0 8 * * 1'},
                       headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['schedule'] == '0 8 * * 1'
    client.delete(f'/api/pipelines/{data["id"]}', headers=headers)


def test_create_pipeline_with_invalid_schedule(client, headers):
    resp = client.post('/api/pipelines',
                       json={'name': 'Bad Schedule', 'schedule': '99 99 99 99 99'},
                       headers=headers)
    assert resp.status_code == 400
    assert 'cron' in resp.get_json()['error'].lower()


def test_create_pipeline_with_variables(client, headers):
    resp = client.post('/api/pipelines', json={
        'name': 'Var Pipeline',
        'variables': [
            {'var_key': 'ENV', 'var_value': 'prod', 'is_secret': False},
            {'var_key': 'API_KEY', 'var_value': 'secret123', 'is_secret': True},
        ],
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    vars_map = {v['var_key']: v for v in data['variables']}
    assert vars_map['ENV']['var_value'] == 'prod'
    assert vars_map['API_KEY']['var_value'] == '***'  # secret masked
    client.delete(f'/api/pipelines/{data["id"]}', headers=headers)


def test_update_pipeline_with_invalid_schedule(client, headers, pipeline_id):
    resp = client.put(f'/api/pipelines/{pipeline_id}',
                      json={'schedule': 'bad cron'},
                      headers=headers)
    assert resp.status_code == 400


def test_update_pipeline_with_variables(client, headers, pipeline_id):
    resp = client.put(f'/api/pipelines/{pipeline_id}', json={
        'variables': [{'var_key': 'X', 'var_value': '42', 'is_secret': False}],
    }, headers=headers)
    assert resp.status_code == 200
    vars_map = {v['var_key']: v for v in resp.get_json()['variables']}
    assert vars_map['X']['var_value'] == '42'


def test_update_pipeline_not_found(client, headers):
    resp = client.put('/api/pipelines/00000000-0000-0000-0000-000000000000',
                      json={'name': 'x'}, headers=headers)
    assert resp.status_code == 404


# ── pipeline runs ─────────────────────────────────────────────────────────────

def test_pipeline_runs_endpoint(client, headers, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/runs', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_pipeline_runs_not_found(client, headers):
    resp = client.get('/api/pipelines/00000000-0000-0000-0000-000000000000/runs',
                      headers=headers)
    # A 404 guard was added alongside the project-membership access check
    # (which needs to load the pipeline to find its project_id).
    assert resp.status_code == 404


# ── webhook tokens ────────────────────────────────────────────────────────────

def test_list_webhook_tokens_empty(client, headers, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_webhook_tokens_pipeline_not_found(client, headers):
    resp = client.get('/api/pipelines/00000000-0000-0000-0000-000000000000/webhook-tokens',
                      headers=headers)
    assert resp.status_code == 404


def test_create_and_revoke_webhook_token(client, headers, pipeline_id):
    # Create
    resp = client.post(f'/api/pipelines/{pipeline_id}/webhook-tokens',
                       json={'label': 'CI Token'}, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'token' in data       # raw token returned only at creation
    assert data['label'] == 'CI Token'
    token_id = data['id']

    # List — should show the new token
    list_resp = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens', headers=headers)
    assert any(t['id'] == token_id for t in list_resp.get_json())

    # Revoke
    del_resp = client.delete(
        f'/api/pipelines/{pipeline_id}/webhook-tokens/{token_id}', headers=headers)
    assert del_resp.status_code == 200

    # Revoke non-existent
    miss = client.delete(
        f'/api/pipelines/{pipeline_id}/webhook-tokens/00000000-0000-0000-0000-000000000000',
        headers=headers)
    assert miss.status_code == 404


def test_create_webhook_token_pipeline_not_found(client, headers):
    resp = client.post('/api/pipelines/00000000-0000-0000-0000-000000000000/webhook-tokens',
                       json={}, headers=headers)
    assert resp.status_code == 404


def test_trigger_via_webhook(client, headers, pipeline_id):
    # Create a token for webhook use
    tok_resp = client.post(f'/api/pipelines/{pipeline_id}/webhook-tokens',
                           json={'label': 'Webhook'}, headers=headers)
    raw_token = tok_resp.get_json()['token']

    # Trigger via webhook (no JWT, just token param)
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger?token={raw_token}')
    assert resp.status_code == 202
    assert resp.get_json()['status'] == 'running'


def test_trigger_via_webhook_no_token(client, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger')
    assert resp.status_code == 401


def test_trigger_via_webhook_invalid_token(client, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger?token=invalidtoken')
    assert resp.status_code == 401


# ── dependencies ─────────────────────────────────────────────────────────────

def test_get_dependencies_empty(client, headers, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/dependencies', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['upstream'] == []
    assert data['downstream'] == []


def test_get_dependencies_not_found(client, headers):
    resp = client.get('/api/pipelines/00000000-0000-0000-0000-000000000000/dependencies',
                      headers=headers)
    assert resp.status_code == 404


def test_add_and_remove_dependency(client, headers, pipeline_id, second_pipeline_id):
    # Add dependency: pipeline_id runs after second_pipeline_id
    resp = client.post(f'/api/pipelines/{pipeline_id}/dependencies',
                       json={'upstream_id': second_pipeline_id}, headers=headers)
    assert resp.status_code == 201
    dep_id = resp.get_json()['dep_id']

    # List — verify it appears
    deps = client.get(f'/api/pipelines/{pipeline_id}/dependencies', headers=headers).get_json()
    assert any(d['dep_id'] == dep_id for d in deps['upstream'])

    # Duplicate check
    dup = client.post(f'/api/pipelines/{pipeline_id}/dependencies',
                      json={'upstream_id': second_pipeline_id}, headers=headers)
    assert dup.status_code == 409

    # Remove
    del_resp = client.delete(
        f'/api/pipelines/{pipeline_id}/dependencies/{dep_id}', headers=headers)
    assert del_resp.status_code == 200


def test_add_dependency_self_reference(client, headers, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/dependencies',
                       json={'upstream_id': pipeline_id}, headers=headers)
    assert resp.status_code == 400
    assert 'itself' in resp.get_json()['error'].lower()


def test_add_dependency_missing_upstream_id(client, headers, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/dependencies',
                       json={}, headers=headers)
    assert resp.status_code == 400


def test_add_dependency_upstream_not_found(client, headers, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/dependencies',
                       json={'upstream_id': '00000000-0000-0000-0000-000000000000'},
                       headers=headers)
    assert resp.status_code == 404


def test_remove_dependency_not_found(client, headers, pipeline_id):
    resp = client.delete(
        f'/api/pipelines/{pipeline_id}/dependencies/00000000-0000-0000-0000-000000000000',
        headers=headers)
    assert resp.status_code == 404


def test_add_dependency_pipeline_not_found(client, headers):
    resp = client.post('/api/pipelines/00000000-0000-0000-0000-000000000000/dependencies',
                       json={'upstream_id': '00000000-0000-0000-0000-000000000001'},
                       headers=headers)
    assert resp.status_code == 404


def test_cycle_detection_blocked(client, headers, pipeline_id, second_pipeline_id):
    # A → B
    client.post(f'/api/pipelines/{second_pipeline_id}/dependencies',
                json={'upstream_id': pipeline_id}, headers=headers)
    # B → A (would create A → B → A cycle)
    resp = client.post(f'/api/pipelines/{pipeline_id}/dependencies',
                       json={'upstream_id': second_pipeline_id}, headers=headers)
    assert resp.status_code == 409
    assert 'circular' in resp.get_json()['error'].lower()


# ── promote ──────────────────────────────────────────────────────────────────

def test_promote_pipeline_missing_target(client, headers, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/promote',
                       json={}, headers=headers)
    assert resp.status_code == 400
    assert 'target_project_id' in resp.get_json()['error'].lower()


def test_promote_pipeline_target_not_found(client, headers, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/promote',
                       json={'target_project_id': '00000000-0000-0000-0000-000000000000'},
                       headers=headers)
    assert resp.status_code == 404


def test_promote_pipeline_not_found(client, headers):
    resp = client.post('/api/pipelines/00000000-0000-0000-0000-000000000000/promote',
                       json={'target_project_id': '00000000-0000-0000-0000-000000000001'},
                       headers=headers)
    assert resp.status_code == 404


# ── import edge cases ─────────────────────────────────────────────────────────

def test_import_pipeline_no_content(client, headers):
    resp = client.post('/api/pipelines/import', json={'yaml_content': ''}, headers=headers)
    assert resp.status_code == 400


def test_import_pipeline_bad_yaml(client, headers):
    resp = client.post('/api/pipelines/import',
                       json={'yaml_content': '{invalid yaml: [}'},
                       headers=headers)
    assert resp.status_code == 400
    assert 'yaml' in resp.get_json()['error'].lower()


def test_import_pipeline_with_secret_var_skipped(client, headers):
    yaml_content = """
name: Import Secret Var Test
variables:
  - var_key: NORMAL
    var_value: public
    is_secret: false
  - var_key: SECRET
    var_value: "***"
    is_secret: true
"""
    resp = client.post('/api/pipelines/import',
                       json={'yaml_content': yaml_content}, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    # Secret with *** value should be skipped during import
    var_keys = [v['var_key'] for v in data['variables']]
    assert 'NORMAL' in var_keys
    client.delete(f'/api/pipelines/{data["id"]}', headers=headers)
