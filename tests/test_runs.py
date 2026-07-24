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


# ── dashboard/summary endpoint ────────────────────────────────────────────────

def test_dashboard_summary_returns_200(client, headers):
    resp = client.get('/api/dashboard/summary', headers=headers)
    assert resp.status_code == 200


def test_dashboard_summary_has_pipeline_runs_key(client, headers):
    resp = client.get('/api/dashboard/summary', headers=headers)
    data = resp.get_json()
    assert 'pipeline_runs' in data


def test_dashboard_summary_pipeline_runs_is_dict(client, headers):
    resp = client.get('/api/dashboard/summary', headers=headers)
    data = resp.get_json()
    assert isinstance(data['pipeline_runs'], dict)


def test_dashboard_summary_requires_auth(client):
    resp = client.get('/api/dashboard/summary')
    assert resp.status_code == 401


def test_dashboard_summary_with_project_id_filter(client, headers):
    """project_id filter is accepted without error."""
    resp = client.get(
        '/api/dashboard/summary?project_id=00000000-0000-0000-0000-000000000000',
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['pipeline_runs'] == {}


def test_dashboard_summary_caps_at_14_runs_per_pipeline_in_sql(app, client, headers):
    """The 14-per-pipeline cap must happen in the SQL query (window function),
    not by fetching every run and truncating in Python — this endpoint is
    polled every few seconds by every open dashboard tab."""
    import uuid
    from datetime import UTC, datetime, timedelta

    from flowforge.db.models import PipelineRun, db

    create = client.post('/api/pipelines', json={'name': '__dash_cap__', 'enabled': True},
                          headers=headers)
    pid = create.get_json()['id']
    try:
        with app.app_context():
            base = datetime.now(UTC)
            run_ids = []
            for i in range(20):
                run = PipelineRun(
                    id=str(uuid.uuid4()),
                    pipeline_id=pid,
                    pipeline_name='__dash_cap__',
                    status='success',
                    started_at=base - timedelta(minutes=i),
                    finished_at=base - timedelta(minutes=i) + timedelta(seconds=1),
                    duration_ms=1000,
                    triggered_by='web_ui',
                )
                db.session.add(run)
                run_ids.append(run.id)
            db.session.commit()

        resp = client.get('/api/dashboard/summary', headers=headers)
        assert resp.status_code == 200
        runs = resp.get_json()['pipeline_runs'][pid]

        assert len(runs) == 14
        # Most recent first, and it's specifically the 14 most recent (not an
        # arbitrary/unordered subset) — confirms ORDER BY happens before the cap.
        assert runs[0]['id'] == run_ids[0]
        assert runs[-1]['id'] == run_ids[13]
    finally:
        with app.app_context():
            db.session.query(PipelineRun).filter(PipelineRun.pipeline_id == pid).delete()
            db.session.commit()
        client.delete(f'/api/pipelines/{pid}', headers=headers)


def test_export_runs_as_csv(client, headers):
    resp = client.get('/api/runs/export?format=csv', headers=headers)
    assert resp.status_code == 200
    assert 'text/csv' in resp.content_type
    assert 'attachment; filename=run_history.csv' in resp.headers.get('Content-Disposition', '')
    
    csv_content = resp.data.decode('utf-8')
    lines = csv_content.strip().split('\n')
    assert len(lines) >= 1
    header = lines[0]
    assert 'Pipeline Name' in header
    assert 'Run ID' in header
    assert 'Status' in header
    assert 'Triggered By' in header


def test_export_runs_with_filters(client, headers):
    resp = client.get('/api/runs/export?format=csv&status=success', headers=headers)
    assert resp.status_code == 200
    assert 'text/csv' in resp.content_type


def test_export_runs_invalid_format(client, headers):
    resp = client.get('/api/runs/export?format=xlsx', headers=headers)
    assert resp.status_code == 400
    data = resp.get_json()
    assert 'Only CSV format is supported' in data.get('error', '')


def test_export_runs_requires_auth(client):
    resp = client.get('/api/runs/export?format=csv')
    assert resp.status_code == 401


def test_export_runs_with_pipeline_id_filter(client, headers):
    resp = client.get(
        '/api/runs/export?format=csv&pipeline_id=00000000-0000-0000-0000-000000000000',
        headers=headers,
    )
    assert resp.status_code == 200
    assert 'text/csv' in resp.content_type


def test_export_runs_with_project_id_filter(client, headers):
    resp = client.get(
        '/api/runs/export?format=csv&project_id=00000000-0000-0000-0000-000000000000',
        headers=headers,
    )
    assert resp.status_code == 200
    assert 'text/csv' in resp.content_type


def test_export_runs_with_explicit_limit(client, headers):
    resp = client.get('/api/runs/export?format=csv&limit=5', headers=headers)
    assert resp.status_code == 200
    assert 'text/csv' in resp.content_type


def test_export_runs_invalid_limit(client, headers):
    resp = client.get('/api/runs/export?format=csv&limit=abc', headers=headers)
    assert resp.status_code == 400
    assert 'integer' in resp.get_json().get('error', '').lower()


def test_export_runs_data_rows_present(client, headers):
    """Trigger a run so the CSV row-writing loop body is exercised."""
    create = client.post(
        '/api/pipelines',
        json={'name': 'CSV Export Coverage Pipeline'},
        headers=headers,
    )
    assert create.status_code == 201
    pid = create.get_json()['id']

    # launch_run commits a 'running' record immediately before async dispatch
    client.post(f'/api/pipelines/{pid}/run', headers=headers)

    resp = client.get(f'/api/runs/export?format=csv&pipeline_id={pid}', headers=headers)
    assert resp.status_code == 200
    lines = resp.data.decode().strip().split('\n')
    assert len(lines) >= 2  # header + at least one data row

    client.delete(f'/api/pipelines/{pid}', headers=headers)
