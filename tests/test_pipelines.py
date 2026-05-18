"""Tests for pipeline and step CRUD."""
import pytest


PIPELINE_PAYLOAD = {
    'name': 'Test Pipeline',
    'description': 'Created by automated test',
    'enabled': True,
    'schedule': None,
}

STEP_PAYLOAD = {
    'name': 'Test Step',
    'step_type': 'db_query',
    'step_order': 1,
    'config': {'query': 'SELECT 1', 'connection_id': None},
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


# ── Pipeline CRUD ─────────────────────────────────────────────────────────────

def test_list_pipelines(client, headers):
    resp = client.get('/api/pipelines', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_pipeline(client, headers):
    resp = client.post('/api/pipelines', json=PIPELINE_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Pipeline'
    assert data['enabled'] is True
    assert 'id' in data
    client.delete(f'/api/pipelines/{data["id"]}', headers=headers)


def test_create_pipeline_missing_name(client, headers):
    resp = client.post('/api/pipelines', json={'description': 'no name'}, headers=headers)
    assert resp.status_code == 400


def test_get_pipeline(client, headers, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == pipeline_id
    assert 'steps' in data


def test_update_pipeline(client, headers, pipeline_id):
    resp = client.put(f'/api/pipelines/{pipeline_id}',
                      json={'name': 'Renamed Pipeline', 'enabled': False}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Renamed Pipeline'
    assert data['enabled'] is False


def test_delete_pipeline(client, headers):
    resp = client.post('/api/pipelines', json=PIPELINE_PAYLOAD, headers=headers)
    pid = resp.get_json()['id']
    del_resp = client.delete(f'/api/pipelines/{pid}', headers=headers)
    assert del_resp.status_code == 200
    get_resp = client.get(f'/api/pipelines/{pid}', headers=headers)
    assert get_resp.status_code == 404


def test_get_nonexistent_pipeline(client, headers):
    resp = client.get('/api/pipelines/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404


# ── Steps ─────────────────────────────────────────────────────────────────────

def test_add_step_to_pipeline(client, headers, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/steps',
                       json=STEP_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Step'
    assert data['step_type'] == 'db_query'
    assert 'id' in data


def test_pipeline_includes_steps(client, headers, pipeline_id):
    client.post(f'/api/pipelines/{pipeline_id}/steps', json=STEP_PAYLOAD, headers=headers)
    resp = client.get(f'/api/pipelines/{pipeline_id}', headers=headers)
    pipeline = resp.get_json()
    assert len(pipeline['steps']) >= 1
    assert pipeline['steps'][0]['name'] == 'Test Step'


def test_update_step(client, headers, pipeline_id):
    create_resp = client.post(f'/api/pipelines/{pipeline_id}/steps',
                              json=STEP_PAYLOAD, headers=headers)
    step_id = create_resp.get_json()['id']
    resp = client.put(f'/api/pipeline-steps/{step_id}',
                      json={'name': 'Renamed Step'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Renamed Step'


def test_delete_step(client, headers, pipeline_id):
    create_resp = client.post(f'/api/pipelines/{pipeline_id}/steps',
                              json=STEP_PAYLOAD, headers=headers)
    step_id = create_resp.get_json()['id']
    del_resp = client.delete(f'/api/pipeline-steps/{step_id}', headers=headers)
    assert del_resp.status_code == 200
