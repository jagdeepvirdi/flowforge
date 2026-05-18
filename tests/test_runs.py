"""Tests for run history endpoints."""


def test_list_runs(client, headers):
    resp = client.get('/api/runs', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_list_runs_with_limit(client, headers):
    resp = client.get('/api/runs?limit=5', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) <= 5


def test_list_runs_filter_status(client, headers):
    resp = client.get('/api/runs?status=success', headers=headers)
    assert resp.status_code == 200
    for run in resp.get_json():
        assert run['status'] == 'success'


def test_get_nonexistent_run(client, headers):
    resp = client.get('/api/runs/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404


def test_trigger_run_nonexistent_pipeline(client, headers):
    resp = client.post('/api/pipelines/00000000-0000-0000-0000-000000000000/run',
                       headers=headers)
    assert resp.status_code == 404


def test_trigger_run_disabled_pipeline(client, headers):
    """A disabled pipeline should refuse to run."""
    create = client.post('/api/pipelines',
                         json={'name': 'Disabled', 'enabled': False}, headers=headers)
    pid = create.get_json()['id']
    run = client.post(f'/api/pipelines/{pid}/run', headers=headers)
    # Should return 400 or 409 — pipeline is disabled
    assert run.status_code in (400, 409)
    client.delete(f'/api/pipelines/{pid}', headers=headers)
