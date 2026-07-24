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


def test_list_pipelines_respects_limit(client, headers, pipeline_id):
    resp = client.get('/api/pipelines?limit=1', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) <= 1


def test_list_pipelines_limit_is_capped_at_500(client, headers):
    resp = client.get('/api/pipelines?limit=999999', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) <= 500


def test_list_pipelines_offset_skips_results(client, headers, pipeline_id):
    all_names = [p['name'] for p in client.get('/api/pipelines?limit=500', headers=headers).get_json()]
    offset_names = [p['name'] for p in
                     client.get('/api/pipelines?limit=500&offset=1', headers=headers).get_json()]
    assert offset_names == all_names[1:]


def test_list_pipelines_does_not_n_plus_one(client, headers, app):
    """Regression test for PERF-01.

    serializers.pipeline_dict() walks each pipeline's steps, variables,
    upstream_deps, and downstream_deps (each dependency also reads its linked
    Pipeline's .name). Left unguarded, GET /api/pipelines issues one query per
    relationship *per pipeline row*; with eager loading it must issue at most
    one query per relationship for the whole page, regardless of row count.
    """
    import uuid

    from sqlalchemy import event

    from flowforge.db.models import db

    created_ids = []
    try:
        for i in range(6):
            resp = client.post('/api/pipelines', json={
                'name': f'perf01-nplus1-{i}-{uuid.uuid4()}',
                'variables': [{'var_key': 'v', 'var_value': str(i), 'is_secret': False}],
            }, headers=headers)
            assert resp.status_code == 201, resp.get_json()
            pid = resp.get_json()['id']
            created_ids.append(pid)
            step_resp = client.post(f'/api/pipelines/{pid}/steps', json=STEP_PAYLOAD, headers=headers)
            assert step_resp.status_code == 201, step_resp.get_json()

        for downstream, upstream in zip(created_ids[1:], created_ids[:-1]):
            dep_resp = client.post(f'/api/pipelines/{downstream}/dependencies',
                                    json={'upstream_id': upstream}, headers=headers)
            assert dep_resp.status_code == 201, dep_resp.get_json()

        with app.app_context():
            engine = db.engine

        statements = []

        def _capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, 'before_cursor_execute', _capture)
        try:
            resp = client.get('/api/pipelines?limit=500', headers=headers)
        finally:
            event.remove(engine, 'before_cursor_execute', _capture)

        assert resp.status_code == 200

        def _count(table):
            return sum(1 for s in statements if table in s)

        # selectinload issues one `WHERE pipeline_id IN (...)` (or equivalent)
        # query per relationship for the whole page — not one per pipeline row.
        assert _count('ff_pipeline_steps') <= 1, statements
        assert _count('ff_pipeline_variables') <= 1, statements
        # ff_pipeline_dependencies is queried twice: once for upstream_deps,
        # once for downstream_deps (distinct FK directions on the same table).
        assert _count('ff_pipeline_dependencies') <= 2, statements
    finally:
        for pid in created_ids:
            client.delete(f'/api/pipelines/{pid}', headers=headers)


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


import yaml


def test_clone_pipeline(client, headers, pipeline_id):
    # Add a step to the pipeline so we can test that it clones steps too
    client.post(f'/api/pipelines/{pipeline_id}/steps', json=STEP_PAYLOAD, headers=headers)
    
    resp = client.post(f'/api/pipelines/{pipeline_id}/clone', headers=headers)
    assert resp.status_code == 201
    cloned = resp.get_json()
    assert cloned['name'] == 'Test Pipeline (Copy)'
    assert cloned['id'] != pipeline_id
    assert len(cloned['steps']) >= 1
    assert cloned['steps'][0]['name'] == 'Test Step'
    
    # Clean up the cloned pipeline
    client.delete(f'/api/pipelines/{cloned["id"]}', headers=headers)


def test_clone_nonexistent_pipeline(client, headers):
    resp = client.post('/api/pipelines/00000000-0000-0000-0000-000000000000/clone', headers=headers)
    assert resp.status_code == 404


def test_export_pipeline(client, headers, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/export', headers=headers)
    assert resp.status_code == 200
    export_data = yaml.safe_load(resp.data)
    assert export_data['name'] == 'Test Pipeline'


def test_export_nonexistent_pipeline(client, headers):
    resp = client.get('/api/pipelines/00000000-0000-0000-0000-000000000000/export', headers=headers)
    assert resp.status_code == 404


def test_import_pipeline(client, headers):
    yaml_content = """
    name: Imported Pipeline
    description: From YAML
    enabled: true
    variables:
      - var_key: env
        var_value: prod
        is_secret: false
    steps:
      - name: Imported Step
        step_type: db_query
        config:
          sql: SELECT 1
        on_error: stop
    """
    resp = client.post('/api/pipelines/import', json={'yaml_content': yaml_content}, headers=headers)
    assert resp.status_code == 201
    pipeline = resp.get_json()
    assert pipeline['name'] == 'Imported Pipeline'
    assert len(pipeline['steps']) == 1
    assert pipeline['steps'][0]['name'] == 'Imported Step'
    
    # Cleanup
    client.delete(f'/api/pipelines/{pipeline["id"]}', headers=headers)


def test_import_pipeline_invalid_format(client, headers):
    resp = client.post('/api/pipelines/import', json={'yaml_content': 'invalid:\n yaml\n  data'}, headers=headers)
    assert resp.status_code == 400


def test_import_pipeline_missing_name(client, headers):
    resp = client.post('/api/pipelines/import', json={'yaml_content': 'enabled: true'}, headers=headers)
    assert resp.status_code == 400

