"""Tests for Multi-Project Support — CRUD, scoping, migration safety."""
import pytest

from flowforge.db.models import DEFAULT_PROJECT_ID

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def project_id(client, headers):
    resp = client.post('/api/projects', json={'name': 'Test Project', 'color': '#3B82F6'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/projects/{pid}', headers=headers)


@pytest.fixture
def project_a(client, headers):
    resp = client.post('/api/projects', json={'name': 'Project Alpha', 'color': '#22C55E'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/projects/{pid}', headers=headers)


@pytest.fixture
def project_b(client, headers):
    resp = client.post('/api/projects', json={'name': 'Project Beta', 'color': '#A855F7'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/projects/{pid}', headers=headers)


# ── Project CRUD ──────────────────────────────────────────────────────────────

def test_list_projects_returns_list(client, headers):
    resp = client.get('/api/projects', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_list_projects_includes_default(client, headers):
    projects = client.get('/api/projects', headers=headers).get_json()
    defaults = [p for p in projects if p['is_default']]
    assert len(defaults) == 1
    assert defaults[0]['id'] == DEFAULT_PROJECT_ID


def test_list_projects_default_first(client, headers):
    projects = client.get('/api/projects', headers=headers).get_json()
    assert projects[0]['is_default'] is True


def test_list_projects_includes_resource_counts(client, headers):
    projects = client.get('/api/projects', headers=headers).get_json()
    for p in projects:
        assert 'resource_counts' in p
        counts = p['resource_counts']
        assert 'pipelines' in counts
        assert 'reports' in counts
        assert 'emails' in counts
        assert 'recipients' in counts


def test_create_project(client, headers):
    resp = client.post('/api/projects', json={'name': 'Finance', 'description': 'Finance team', 'color': '#F97316'}, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Finance'
    assert data['description'] == 'Finance team'
    assert data['color'] == '#F97316'
    assert data['is_default'] is False
    assert 'id' in data
    client.delete(f'/api/projects/{data["id"]}', headers=headers)


def test_create_project_missing_name(client, headers):
    resp = client.post('/api/projects', json={'color': '#FF0000'}, headers=headers)
    assert resp.status_code == 400


def test_get_project_with_resource_counts(client, headers, project_id):
    resp = client.get(f'/api/projects/{project_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == project_id
    assert 'resource_counts' in data
    counts = data['resource_counts']
    assert counts['pipelines'] == 0
    assert counts['reports'] == 0
    assert counts['emails'] == 0
    assert counts['recipients'] == 0


def test_get_nonexistent_project(client, headers):
    resp = client.get('/api/projects/00000000-0000-0000-0000-000000000099', headers=headers)
    assert resp.status_code == 404


def test_patch_project(client, headers, project_id):
    resp = client.patch(f'/api/projects/{project_id}',
                        json={'name': 'Renamed', 'color': '#EF4444'}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Renamed'
    assert data['color'] == '#EF4444'


def test_delete_project(client, headers):
    resp = client.post('/api/projects', json={'name': 'Temp Project'}, headers=headers)
    pid = resp.get_json()['id']
    assert client.delete(f'/api/projects/{pid}', headers=headers).status_code == 200
    assert client.get(f'/api/projects/{pid}', headers=headers).status_code == 404


def test_cannot_delete_default_project(client, headers):
    resp = client.delete(f'/api/projects/{DEFAULT_PROJECT_ID}', headers=headers)
    assert resp.status_code == 400
    assert 'Default' in resp.get_json()['error']


def test_cannot_delete_project_with_resources(client, headers, project_id):
    pipeline_resp = client.post('/api/pipelines',
                                json={'name': 'Scoped Pipeline', 'project_id': project_id},
                                headers=headers)
    assert pipeline_resp.status_code == 201
    pipeline_id = pipeline_resp.get_json()['id']

    del_resp = client.delete(f'/api/projects/{project_id}', headers=headers)
    assert del_resp.status_code == 409
    assert 'resource_counts' in del_resp.get_json()

    client.delete(f'/api/pipelines/{pipeline_id}', headers=headers)


# ── Default project assignment ────────────────────────────────────────────────

def test_pipeline_without_project_id_assigned_to_default(client, headers):
    resp = client.post('/api/pipelines', json={'name': 'No Project Pipeline'}, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['project_id'] == DEFAULT_PROJECT_ID
    client.delete(f'/api/pipelines/{data["id"]}', headers=headers)


def test_pipeline_with_explicit_project_id_assigned_correctly(client, headers, project_id):
    resp = client.post('/api/pipelines',
                       json={'name': 'Scoped Pipeline', 'project_id': project_id},
                       headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['project_id'] == project_id
    client.delete(f'/api/pipelines/{data["id"]}', headers=headers)


def test_recipient_group_without_project_id_assigned_to_default(client, headers):
    resp = client.post('/api/recipient-groups',
                       json={'name': 'No-Project Group', 'addresses': ['x@x.com']},
                       headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['project_id'] == DEFAULT_PROJECT_ID
    client.delete(f'/api/recipient-groups/{data["id"]}', headers=headers)


# ── Project scoping — no cross-project leakage ────────────────────────────────

def test_pipelines_scoped_by_project_id(client, headers, project_a, project_b):
    pa = client.post('/api/pipelines',
                     json={'name': 'Alpha Pipeline', 'project_id': project_a},
                     headers=headers).get_json()
    pb = client.post('/api/pipelines',
                     json={'name': 'Beta Pipeline', 'project_id': project_b},
                     headers=headers).get_json()

    resp_a = client.get(f'/api/pipelines?project_id={project_a}', headers=headers).get_json()
    resp_b = client.get(f'/api/pipelines?project_id={project_b}', headers=headers).get_json()

    ids_a = {p['id'] for p in resp_a}
    ids_b = {p['id'] for p in resp_b}

    assert pa['id'] in ids_a
    assert pb['id'] not in ids_a   # Beta pipeline NOT in Alpha results

    assert pb['id'] in ids_b
    assert pa['id'] not in ids_b   # Alpha pipeline NOT in Beta results

    client.delete(f'/api/pipelines/{pa["id"]}', headers=headers)
    client.delete(f'/api/pipelines/{pb["id"]}', headers=headers)


def test_pipelines_unfiltered_returns_all(client, headers, project_a, project_b):
    pa = client.post('/api/pipelines',
                     json={'name': 'Alpha Pipeline 2', 'project_id': project_a},
                     headers=headers).get_json()
    pb = client.post('/api/pipelines',
                     json={'name': 'Beta Pipeline 2', 'project_id': project_b},
                     headers=headers).get_json()

    all_pipelines = client.get('/api/pipelines', headers=headers).get_json()
    all_ids = {p['id'] for p in all_pipelines}

    assert pa['id'] in all_ids
    assert pb['id'] in all_ids

    client.delete(f'/api/pipelines/{pa["id"]}', headers=headers)
    client.delete(f'/api/pipelines/{pb["id"]}', headers=headers)


def test_recipient_groups_scoped_by_project_id(client, headers, project_a, project_b):
    ga = client.post('/api/recipient-groups',
                     json={'name': 'Alpha Group', 'addresses': ['a@a.com'], 'project_id': project_a},
                     headers=headers).get_json()
    gb = client.post('/api/recipient-groups',
                     json={'name': 'Beta Group', 'addresses': ['b@b.com'], 'project_id': project_b},
                     headers=headers).get_json()

    ids_a = {g['id'] for g in client.get(f'/api/recipient-groups?project_id={project_a}', headers=headers).get_json()}
    ids_b = {g['id'] for g in client.get(f'/api/recipient-groups?project_id={project_b}', headers=headers).get_json()}

    assert ga['id'] in ids_a
    assert gb['id'] not in ids_a
    assert gb['id'] in ids_b
    assert ga['id'] not in ids_b

    client.delete(f'/api/recipient-groups/{ga["id"]}', headers=headers)
    client.delete(f'/api/recipient-groups/{gb["id"]}', headers=headers)


def test_runs_scoped_by_project_id(client, headers, project_a, project_b):
    pa = client.post('/api/pipelines',
                     json={'name': 'Alpha Run Pipeline', 'project_id': project_a},
                     headers=headers).get_json()
    pb = client.post('/api/pipelines',
                     json={'name': 'Beta Run Pipeline', 'project_id': project_b},
                     headers=headers).get_json()

    run_a = client.post(f'/api/pipelines/{pa["id"]}/run', headers=headers).get_json()
    run_b = client.post(f'/api/pipelines/{pb["id"]}/run', headers=headers).get_json()

    runs_a = client.get(f'/api/runs?project_id={project_a}', headers=headers).get_json()
    runs_b = client.get(f'/api/runs?project_id={project_b}', headers=headers).get_json()

    ids_a = {r['id'] for r in runs_a}
    ids_b = {r['id'] for r in runs_b}

    assert run_a['run_id'] in ids_a
    assert run_b['run_id'] not in ids_a
    assert run_b['run_id'] in ids_b
    assert run_a['run_id'] not in ids_b

    client.delete(f'/api/pipelines/{pa["id"]}', headers=headers)
    client.delete(f'/api/pipelines/{pb["id"]}', headers=headers)


def test_resource_counts_reflect_actual_resources(client, headers, project_id):
    p1 = client.post('/api/pipelines',
                     json={'name': 'Count Test Pipeline', 'project_id': project_id},
                     headers=headers).get_json()
    g1 = client.post('/api/recipient-groups',
                     json={'name': 'Count Test Group', 'addresses': ['x@x.com'], 'project_id': project_id},
                     headers=headers).get_json()

    counts = client.get(f'/api/projects/{project_id}', headers=headers).get_json()['resource_counts']
    assert counts['pipelines'] == 1
    assert counts['recipients'] == 1

    client.delete(f'/api/pipelines/{p1["id"]}', headers=headers)
    client.delete(f'/api/recipient-groups/{g1["id"]}', headers=headers)

    counts_after = client.get(f'/api/projects/{project_id}', headers=headers).get_json()['resource_counts']
    assert counts_after['pipelines'] == 0
    assert counts_after['recipients'] == 0


# ── Migration safety ──────────────────────────────────────────────────────────

def test_default_project_has_fixed_uuid(client, headers):
    projects = client.get('/api/projects', headers=headers).get_json()
    default = next(p for p in projects if p['is_default'])
    assert default['id'] == DEFAULT_PROJECT_ID


def test_new_pipelines_without_project_go_to_default_and_appear_in_its_list(client, headers):
    resp = client.post('/api/pipelines', json={'name': 'Default-bound Pipeline'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']

    scoped = client.get(f'/api/pipelines?project_id={DEFAULT_PROJECT_ID}', headers=headers).get_json()
    assert any(p['id'] == pid for p in scoped)

    client.delete(f'/api/pipelines/{pid}', headers=headers)
