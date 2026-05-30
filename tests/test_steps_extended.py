"""Extended tests for pipeline step CRUD — covers validation and step_order swap."""
import pytest


PIPELINE_PAYLOAD = {'name': '__steps_ext__', 'enabled': True}
STEP_PAYLOAD = {
    'name': 'Query Step',
    'step_type': 'db_query',
    'step_order': 1,
    'config': {'query': 'SELECT 1'},
    'on_error': 'stop',
    'enabled': True,
}


@pytest.fixture
def pipeline_id(client, headers):
    resp = client.post('/api/pipelines', json=PIPELINE_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/pipelines/{pid}', headers=headers)


@pytest.fixture
def step_id(client, headers, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/steps', json=STEP_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    return resp.get_json()['id']


# ── GET /pipelines/:id/steps ──────────────────────────────────────────────────

def test_list_steps_empty(client, headers, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/steps', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_steps_returns_added_step(client, headers, pipeline_id, step_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/steps', headers=headers)
    assert resp.status_code == 200
    steps = resp.get_json()
    assert len(steps) == 1
    assert steps[0]['id'] == step_id


def test_list_steps_nonexistent_pipeline(client, headers):
    resp = client.get(
        '/api/pipelines/00000000-0000-0000-0000-000000000010/steps',
        headers=headers,
    )
    assert resp.status_code == 404


def test_list_steps_requires_auth(client, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/steps')
    assert resp.status_code == 401


# ── POST /pipelines/:id/steps ─────────────────────────────────────────────────

def test_add_step_invalid_type_returns_400(client, headers, pipeline_id):
    resp = client.post(
        f'/api/pipelines/{pipeline_id}/steps',
        json={**STEP_PAYLOAD, 'step_type': 'invalid_type'},
        headers=headers,
    )
    assert resp.status_code == 400
    assert 'step_type' in resp.get_json()['error'].lower()


def test_add_step_missing_name_returns_400(client, headers, pipeline_id):
    payload = {k: v for k, v in STEP_PAYLOAD.items() if k != 'name'}
    resp = client.post(
        f'/api/pipelines/{pipeline_id}/steps',
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    assert 'name' in resp.get_json()['error'].lower()


def test_add_step_nonexistent_pipeline_returns_404(client, headers):
    resp = client.post(
        '/api/pipelines/00000000-0000-0000-0000-000000000010/steps',
        json=STEP_PAYLOAD,
        headers=headers,
    )
    assert resp.status_code == 404


def test_add_step_all_valid_types(client, headers, pipeline_id):
    valid_types = [
        'db_procedure', 'db_query', 'report', 'email', 'drive_upload',
        'onedrive_upload', 'ai_analyze', 'data_load', 'bulk_load', 'sftp_transfer',
        'ssh_command', 'db_health_check', 'data_report', 'ssh_health_check',
    ]
    created_ids = []
    for stype in valid_types:
        resp = client.post(
            f'/api/pipelines/{pipeline_id}/steps',
            json={'name': f'{stype} step', 'step_type': stype},
            headers=headers,
        )
        assert resp.status_code == 201, f'{stype} should be accepted'
        created_ids.append(resp.get_json()['id'])
    for sid in created_ids:
        client.delete(f'/api/pipeline-steps/{sid}', headers=headers)


def test_add_step_auto_increments_order(client, headers, pipeline_id):
    r1 = client.post(f'/api/pipelines/{pipeline_id}/steps',
                     json={'name': 'Step A', 'step_type': 'db_query'}, headers=headers)
    r2 = client.post(f'/api/pipelines/{pipeline_id}/steps',
                     json={'name': 'Step B', 'step_type': 'email'}, headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r2.get_json()['step_order'] > r1.get_json()['step_order']
    client.delete(f'/api/pipeline-steps/{r1.get_json()["id"]}', headers=headers)
    client.delete(f'/api/pipeline-steps/{r2.get_json()["id"]}', headers=headers)


# ── PUT /pipeline-steps/:id ───────────────────────────────────────────────────

def test_update_step_invalid_type_returns_400(client, headers, step_id):
    resp = client.put(
        f'/api/pipeline-steps/{step_id}',
        json={'step_type': 'not_a_real_type'},
        headers=headers,
    )
    assert resp.status_code == 400


def test_update_step_nonexistent_returns_404(client, headers):
    resp = client.put(
        '/api/pipeline-steps/00000000-0000-0000-0000-000000000020',
        json={'name': 'Ghost'},
        headers=headers,
    )
    assert resp.status_code == 404


def test_update_step_config(client, headers, step_id):
    resp = client.put(
        f'/api/pipeline-steps/{step_id}',
        json={'config': {'query': 'SELECT 2', 'output_table': 'staging.x'}},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()['config']['output_table'] == 'staging.x'


def test_update_step_on_error(client, headers, step_id):
    resp = client.put(
        f'/api/pipeline-steps/{step_id}',
        json={'on_error': 'continue'},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()['on_error'] == 'continue'


def test_update_step_order_swap(client, headers, pipeline_id):
    """Moving a step to an occupied order swaps without violating the unique constraint."""
    r1 = client.post(f'/api/pipelines/{pipeline_id}/steps',
                     json={'name': 'Step 1', 'step_type': 'db_query', 'step_order': 1},
                     headers=headers)
    r2 = client.post(f'/api/pipelines/{pipeline_id}/steps',
                     json={'name': 'Step 2', 'step_type': 'email', 'step_order': 2},
                     headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    s1_id = r1.get_json()['id']
    s2_id = r2.get_json()['id']

    # Move step 2 to order 1 — should swap them
    resp = client.put(
        f'/api/pipeline-steps/{s2_id}',
        json={'step_order': 1},
        headers=headers,
    )
    assert resp.status_code == 200

    # Verify: step 2 is now at order 1
    assert resp.get_json()['step_order'] == 1

    client.delete(f'/api/pipeline-steps/{s1_id}', headers=headers)
    client.delete(f'/api/pipeline-steps/{s2_id}', headers=headers)


def test_update_step_enabled_flag(client, headers, step_id):
    resp = client.put(
        f'/api/pipeline-steps/{step_id}',
        json={'enabled': False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()['enabled'] is False


def test_update_step_requires_auth(client, step_id):
    resp = client.put(f'/api/pipeline-steps/{step_id}', json={'name': 'no auth'})
    assert resp.status_code == 401


# ── DELETE /pipeline-steps/:id ────────────────────────────────────────────────

def test_delete_step_nonexistent_returns_404(client, headers):
    resp = client.delete(
        '/api/pipeline-steps/00000000-0000-0000-0000-000000000030',
        headers=headers,
    )
    assert resp.status_code == 404


def test_delete_step_requires_auth(client, step_id):
    resp = client.delete(f'/api/pipeline-steps/{step_id}')
    assert resp.status_code == 401
