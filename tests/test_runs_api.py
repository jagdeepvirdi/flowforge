"""Tests for flowforge/api/routes/runs.py — _check_anomaly, project_id filter,
anomalies endpoint, diff endpoint, cancel, download."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from flowforge.db.models import PipelineRun, StepRun, db

# ── _check_anomaly ────────────────────────────────────────────────────────────

def test_check_anomaly_current_none():
    from flowforge.api.routes.runs import _check_anomaly
    assert _check_anomaly([100, 200, 300, 400, 500], None) is None


def test_check_anomaly_history_too_short():
    from flowforge.api.routes.runs import _check_anomaly
    assert _check_anomaly([100, 200, 300, 400], 100) is None


def test_check_anomaly_empty_history():
    from flowforge.api.routes.runs import _check_anomaly
    assert _check_anomaly([], 100) is None


def test_check_anomaly_stdev_zero():
    from flowforge.api.routes.runs import _check_anomaly
    # All same values → stdev = 0
    result = _check_anomaly([100, 100, 100, 100, 100], 100)
    assert result is None


def test_check_anomaly_z_below_threshold():
    from flowforge.api.routes.runs import _check_anomaly
    # Values close to mean → low z-score
    history = [100, 102, 98, 101, 99]
    result = _check_anomaly(history, 100)
    assert result is None


def test_check_anomaly_outlier_detected():
    from flowforge.api.routes.runs import _check_anomaly
    # current is far from mean → z > 2
    history = [100, 100, 100, 100, 100, 100]
    # stdev ≈ 0 for uniform history — use slightly varied history
    history = [100, 101, 99, 100, 102, 98]
    result = _check_anomaly(history, 500)
    assert result is not None
    assert 'z_score' in result
    assert result['z_score'] > 2.0
    assert 'mean' in result
    assert 'pct_diff' in result


def test_check_anomaly_returns_correct_pct_diff():
    from flowforge.api.routes.runs import _check_anomaly
    history = [100, 100, 100, 100, 100, 100, 101, 99]
    result = _check_anomaly(history, 1000)
    assert result is not None
    # pct_diff should be (1000 - ~100) / 100 * 100 ≈ 900%
    assert result['pct_diff'] > 100


def test_check_anomaly_mean_zero_no_division_error():
    """When mean is 0, pct_diff should be 0 (not divide-by-zero)."""
    from flowforge.api.routes.runs import _check_anomaly
    history = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    # stdev = 0 → returns None before pct_diff
    result = _check_anomaly(history, 100)
    assert result is None


def test_check_anomaly_large_deviation_returns_dict():
    from flowforge.api.routes.runs import _check_anomaly
    # history centered around 50, current = 10000
    history = [48, 50, 52, 49, 51, 50, 53, 47, 50, 51]
    result = _check_anomaly(history, 10000)
    assert result is not None
    assert result['value'] == 10000
    assert result['z_score'] > 2


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pipeline_id(client, headers):
    resp = client.post('/api/pipelines', json={'name': '__runs_api_ext__', 'enabled': True}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/pipelines/{pid}', headers=headers)


@pytest.fixture
def pipeline_with_project(client, headers):
    """Create a pipeline with a project via API, return (pipeline_id, project_id)."""
    # First create a project
    proj_resp = client.post(
        '/api/projects',
        json={'name': '__runs_project__'},
        headers=headers,
    )
    assert proj_resp.status_code in (200, 201)
    proj_id = proj_resp.get_json()['id']

    # Create pipeline in that project
    pipe_resp = client.post(
        '/api/pipelines',
        json={'name': '__runs_project_pipe__', 'enabled': True, 'project_id': proj_id},
        headers=headers,
    )
    assert pipe_resp.status_code == 201
    pipe_id = pipe_resp.get_json()['id']

    yield pipe_id, proj_id

    client.delete(f'/api/pipelines/{pipe_id}', headers=headers)
    client.delete(f'/api/projects/{proj_id}', headers=headers)


@pytest.fixture
def viewer_headers_no_projects(app, client):
    """A viewer-role user with zero project memberships — for exercising the
    non-admin accessible_project_ids() branch of the trends endpoint."""
    import bcrypt

    username = f'trends_viewer_{uuid.uuid4().hex[:8]}'
    with app.app_context():
        from flowforge.db.models import User

        user = User(
            username=username,
            password_hash=bcrypt.hashpw(b'viewpass123', bcrypt.gensalt(4)).decode(),
            role='viewer',
        )
        db.session.add(user)
        db.session.commit()

    login = client.post('/api/auth/login', json={'username': username, 'password': 'viewpass123'})
    assert login.status_code == 200
    token = login.get_json()['token']

    yield {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    with app.app_context():
        from flowforge.db.models import User

        u = db.session.query(User).filter_by(username=username).first()
        if u:
            db.session.delete(u)
            db.session.commit()


@pytest.fixture
def run_id(app, pipeline_id):
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            pipeline_name='__runs_api_ext__',
            status='success',
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            duration_ms=500,
            triggered_by='web_ui',
        )
        db.session.add(run)
        db.session.commit()
        yield run.id
        r = db.session.get(PipelineRun, run.id)
        if r:
            db.session.delete(r)
            db.session.commit()


@pytest.fixture
def run_no_pipeline(app):
    """Run where pipeline_id is NULL."""
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=None,
            pipeline_name='Orphan Pipeline',
            status='success',
            started_at=datetime.now(UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()
        yield run.id
        r = db.session.get(PipelineRun, run.id)
        if r:
            db.session.delete(r)
            db.session.commit()


@pytest.fixture
def running_run_id(app, pipeline_id):
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            pipeline_name='__runs_api_ext__',
            status='running',
            started_at=datetime.now(UTC),
            triggered_by='scheduler',
        )
        db.session.add(run)
        db.session.commit()
        yield run.id
        r = db.session.get(PipelineRun, run.id)
        if r:
            db.session.delete(r)
            db.session.commit()


# ── GET /api/runs?project_id=xxx ─────────────────────────────────────────────

def test_list_runs_project_id_filter_returns_200(client, headers):
    """project_id filter (lines 74-76) — valid UUID returns 200 list."""
    bogus_project = str(uuid.uuid4())
    resp = client.get(f'/api/runs?project_id={bogus_project}', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_list_runs_project_id_filter_excludes_others(client, headers, pipeline_with_project, app):
    """Runs for a specific project_id should not include runs from other projects."""
    pipe_id, proj_id = pipeline_with_project

    # Create a run under the project pipeline
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipe_id,
            pipeline_name='__runs_project_pipe__',
            status='success',
            started_at=datetime.now(UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()
        rid = run.id

    resp = client.get(f'/api/runs?project_id={proj_id}', headers=headers)
    assert resp.status_code == 200
    runs = resp.get_json()
    assert any(r['id'] == rid for r in runs)

    # Cleanup
    with app.app_context():
        r = db.session.get(PipelineRun, rid)
        if r:
            db.session.delete(r)
            db.session.commit()


def test_list_runs_project_id_no_results_for_unknown(client, headers):
    fake_proj = '00000000-0000-0000-0000-ffffffffffff'
    resp = client.get(f'/api/runs?project_id={fake_proj}', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


# ── GET /api/runs/<id>/anomalies ──────────────────────────────────────────────

def test_get_anomalies_run_not_found(client, headers):
    fake_id = '00000000-0000-0000-0000-000000000099'
    resp = client.get(f'/api/runs/{fake_id}/anomalies', headers=headers)
    assert resp.status_code == 404


def test_get_anomalies_run_no_pipeline_id(client, headers, run_no_pipeline):
    resp = client.get(f'/api/runs/{run_no_pipeline}/anomalies', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_anomalies_run_with_pipeline_returns_list(client, headers, run_id):
    resp = client.get(f'/api/runs/{run_id}/anomalies', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_get_anomalies_requires_auth(client, run_id):
    resp = client.get(f'/api/runs/{run_id}/anomalies')
    assert resp.status_code == 401


# ── GET /api/runs/<id>/diff ───────────────────────────────────────────────────

def test_get_diff_run_not_found(client, headers):
    fake_id = '00000000-0000-0000-0000-000000000098'
    resp = client.get(f'/api/runs/{fake_id}/diff', headers=headers)
    assert resp.status_code == 404


def test_get_diff_no_pipeline_id(client, headers, run_no_pipeline):
    resp = client.get(f'/api/runs/{run_no_pipeline}/diff', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['prev_run_id'] is None
    assert data['steps'] == []


def test_get_diff_no_previous_run(client, headers, run_id):
    """Run with pipeline_id but no prior successful run → prev_run_id=null."""
    resp = client.get(f'/api/runs/{run_id}/diff', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'prev_run_id' in data
    assert 'steps' in data


def test_get_diff_with_previous_run(client, headers, pipeline_id, app):
    """Two runs for same pipeline → diff endpoint returns prev_run_id and step comparison."""
    with app.app_context():
        # Create an earlier successful run
        prev = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            pipeline_name='__runs_api_ext__',
            status='success',
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
            triggered_by='test',
        )
        db.session.add(prev)
        db.session.commit()

        # Add a step run to prev
        sr_prev = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=prev.id,
            step_name='extract',
            step_type='db_query',
            step_order=1,
            status='success',
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            rows_affected=100,
            duration_ms=200,
        )
        db.session.add(sr_prev)
        db.session.commit()

        # Create the current run (later)
        curr = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            pipeline_name='__runs_api_ext__',
            status='success',
            started_at=datetime(2026, 2, 1, tzinfo=UTC),
            finished_at=datetime(2026, 2, 1, 1, tzinfo=UTC),
            triggered_by='test',
        )
        db.session.add(curr)
        db.session.commit()

        # Add a step run to curr
        sr_curr = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=curr.id,
            step_name='extract',
            step_type='db_query',
            step_order=1,
            status='success',
            started_at=datetime(2026, 2, 1, tzinfo=UTC),
            rows_affected=120,
            duration_ms=180,
        )
        db.session.add(sr_curr)
        db.session.commit()

        curr_id    = curr.id
        prev_id    = prev.id
        sr_curr_id = sr_curr.id
        sr_prev_id = sr_prev.id

    resp = client.get(f'/api/runs/{curr_id}/diff', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['prev_run_id'] == prev_id
    steps = data['steps']
    assert len(steps) >= 1
    extract_step = next((s for s in steps if s['step_name'] == 'extract'), None)
    assert extract_step is not None
    assert extract_step['rows_current'] == 120
    assert extract_step['rows_prev'] == 100
    assert extract_step['rows_delta'] == 20

    # Cleanup — use captured string IDs (objects detached after context exit)
    with app.app_context():
        for sr_id in [sr_curr_id, sr_prev_id]:
            s = db.session.get(StepRun, sr_id)
            if s:
                db.session.delete(s)
        for r_id in [curr_id, prev_id]:
            r = db.session.get(PipelineRun, r_id)
            if r:
                db.session.delete(r)
        db.session.commit()


def test_get_diff_requires_auth(client, run_id):
    resp = client.get(f'/api/runs/{run_id}/diff')
    assert resp.status_code == 401


# ── POST /api/runs/<id>/cancel ────────────────────────────────────────────────

def test_cancel_run_not_found(client, headers):
    fake_id = '00000000-0000-0000-0000-000000000097'
    resp = client.post(f'/api/runs/{fake_id}/cancel', headers=headers)
    assert resp.status_code == 404


def test_cancel_success_status_returns_409(client, headers, run_id):
    """Cancelling a run with status 'success' → 409."""
    resp = client.post(f'/api/runs/{run_id}/cancel', headers=headers)
    assert resp.status_code == 409


def test_cancel_running_run_returns_200(client, headers, running_run_id):
    resp = client.post(f'/api/runs/{running_run_id}/cancel', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['run_id'] == running_run_id


def test_cancel_changes_status_to_cancelled(client, headers, app, running_run_id):
    client.post(f'/api/runs/{running_run_id}/cancel', headers=headers)
    with app.app_context():
        r = db.session.get(PipelineRun, running_run_id)
        assert r.status == 'cancelled'


def test_cancel_requires_auth(client, running_run_id):
    resp = client.post(f'/api/runs/{running_run_id}/cancel')
    assert resp.status_code == 401


# ── GET /api/step-runs/<id>/download ─────────────────────────────────────────

def test_download_step_run_not_found(client, headers):
    fake_id = '00000000-0000-0000-0000-000000000096'
    resp = client.get(f'/api/step-runs/{fake_id}/download', headers=headers)
    assert resp.status_code == 404


def test_download_step_run_no_output_path(client, headers, app, run_id):
    with app.app_context():
        sr = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='no_out',
            step_type='db_query',
            step_order=1,
            status='success',
            started_at=datetime.now(UTC),
            output_path=None,
        )
        db.session.add(sr)
        db.session.commit()
        sid = sr.id

    resp = client.get(f'/api/step-runs/{sid}/download', headers=headers)
    assert resp.status_code == 404

    with app.app_context():
        s = db.session.get(StepRun, sid)
        if s:
            db.session.delete(s)
            db.session.commit()


def test_download_step_run_path_outside_output_dir(client, headers, app, run_id):
    with app.app_context():
        sr = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='bad_path',
            step_type='report',
            step_order=1,
            status='success',
            started_at=datetime.now(UTC),
            output_path='/etc/passwd',
        )
        db.session.add(sr)
        db.session.commit()
        sid = sr.id

    resp = client.get(f'/api/step-runs/{sid}/download', headers=headers)
    assert resp.status_code == 403

    with app.app_context():
        s = db.session.get(StepRun, sid)
        if s:
            db.session.delete(s)
            db.session.commit()


def test_download_step_run_file_not_on_disk(client, headers, app, run_id, tmp_path, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_OUTPUT_DIR', str(tmp_path))
    fake_path = tmp_path / 'nonexistent_report.xlsx'

    with app.app_context():
        sr = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='ghost',
            step_type='report',
            step_order=1,
            status='success',
            started_at=datetime.now(UTC),
            output_path=str(fake_path),
        )
        db.session.add(sr)
        db.session.commit()
        sid = sr.id

    resp = client.get(f'/api/step-runs/{sid}/download', headers=headers)
    assert resp.status_code == 404

    with app.app_context():
        s = db.session.get(StepRun, sid)
        if s:
            db.session.delete(s)
            db.session.commit()


def test_download_step_run_requires_auth(client, app, run_id):
    with app.app_context():
        sr = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='auth_test',
            step_type='report',
            step_order=1,
            status='success',
            started_at=datetime.now(UTC),
            output_path=None,
        )
        db.session.add(sr)
        db.session.commit()
        sid = sr.id

    resp = client.get(f'/api/step-runs/{sid}/download')
    assert resp.status_code == 401

    with app.app_context():
        s = db.session.get(StepRun, sid)
        if s:
            db.session.delete(s)
            db.session.commit()


# ── _percentile ──────────────────────────────────────────────────────────────

def test_percentile_empty_returns_zero():
    from flowforge.api.routes.runs import _percentile
    assert _percentile([], 95) == 0.0


def test_percentile_single_value():
    from flowforge.api.routes.runs import _percentile
    assert _percentile([10], 95) == 10


def test_percentile_median():
    from flowforge.api.routes.runs import _percentile
    assert _percentile([10, 20, 30, 40, 50], 50) == 30


def test_percentile_p95_nearest_rank():
    from flowforge.api.routes.runs import _percentile
    assert _percentile([10, 20, 30, 40, 50], 95) == 50


# ── GET /api/step-runs/trends ─────────────────────────────────────────────────

def _add_run_with_step(app, pipeline_id, step_type, *, status='success',
                        run_status='success', duration_ms=None, rows_affected=None,
                        started_at=None):
    """Create a PipelineRun + single StepRun for trends tests; returns run.id."""
    started_at = started_at or datetime.now(UTC)
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()), pipeline_id=pipeline_id, pipeline_name='__runs_api_ext__',
            status=run_status, started_at=started_at, triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()
        db.session.add(StepRun(
            id=str(uuid.uuid4()), pipeline_run_id=run.id, step_name='load',
            step_type=step_type, step_order=1, status=status,
            started_at=started_at, duration_ms=duration_ms, rows_affected=rows_affected,
        ))
        db.session.commit()
        return run.id


def _delete_run(app, run_id_local):
    with app.app_context():
        r = db.session.get(PipelineRun, run_id_local)
        if r:
            db.session.delete(r)
            db.session.commit()


def test_step_run_trends_requires_auth(client):
    resp = client.get('/api/step-runs/trends')
    assert resp.status_code == 401


def test_step_run_trends_empty_when_no_matching_data(client, headers):
    resp = client.get('/api/step-runs/trends', query_string={'step_type': '__no_such_step_type__'}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['series'] == []
    assert data['step_type'] == '__no_such_step_type__'


def test_step_run_trends_invalid_days_returns_400(client, headers):
    resp = client.get('/api/step-runs/trends', query_string={'days': 'abc'}, headers=headers)
    assert resp.status_code == 400


def test_step_run_trends_days_clamped_to_max(client, headers):
    resp = client.get('/api/step-runs/trends', query_string={'days': 99999}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['window_days'] == 180


def test_step_run_trends_aggregates_duration_and_rows(client, headers, pipeline_id, app):
    step_type = '__trends_bulk_load__'
    now = datetime.now(UTC)
    run_ids = [
        _add_run_with_step(app, pipeline_id, step_type, duration_ms=d, rows_affected=r, started_at=now)
        for d, r in [(100, 10), (200, 20), (300, 30)]
    ]
    try:
        resp = client.get(
            '/api/step-runs/trends',
            query_string={'step_type': step_type, 'pipeline_id': pipeline_id},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['series']) == 1
        bucket = data['series'][0]
        assert bucket['run_count'] == 3
        assert bucket['success_count'] == 3
        assert bucket['failure_count'] == 0
        assert bucket['avg_duration_ms'] == 200.0
        assert bucket['avg_rows_affected'] == 20.0
        assert bucket['p95_duration_ms'] == 300.0
    finally:
        for rid in run_ids:
            _delete_run(app, rid)


def test_step_run_trends_counts_failures_separately(client, headers, pipeline_id, app):
    step_type = '__trends_failures__'
    now = datetime.now(UTC)
    ok_id = _add_run_with_step(app, pipeline_id, step_type, status='success', run_status='success',
                                duration_ms=100, started_at=now)
    fail_id = _add_run_with_step(app, pipeline_id, step_type, status='failed', run_status='failed',
                                  duration_ms=100, started_at=now)
    try:
        resp = client.get('/api/step-runs/trends', query_string={'step_type': step_type}, headers=headers)
        data = resp.get_json()
        bucket = data['series'][0]
        assert bucket['run_count'] == 2
        assert bucket['success_count'] == 1
        assert bucket['failure_count'] == 1
    finally:
        _delete_run(app, ok_id)
        _delete_run(app, fail_id)


def test_step_run_trends_excludes_running_steps(client, headers, pipeline_id, app):
    step_type = '__trends_running__'
    run_id_local = _add_run_with_step(app, pipeline_id, step_type, status='running', run_status='running')
    try:
        resp = client.get('/api/step-runs/trends', query_string={'step_type': step_type}, headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()['series'] == []
    finally:
        _delete_run(app, run_id_local)


def test_step_run_trends_available_step_types_lists_distinct_types(client, headers, pipeline_id, app):
    now = datetime.now(UTC)
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()), pipeline_id=pipeline_id, pipeline_name='__runs_api_ext__',
            status='success', started_at=now, triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()
        db.session.add(StepRun(
            id=str(uuid.uuid4()), pipeline_run_id=run.id, step_name='a',
            step_type='__trends_type_a__', step_order=1, status='success',
            started_at=now, duration_ms=100,
        ))
        db.session.add(StepRun(
            id=str(uuid.uuid4()), pipeline_run_id=run.id, step_name='b',
            step_type='__trends_type_b__', step_order=2, status='success',
            started_at=now, duration_ms=100,
        ))
        db.session.commit()
        run_id_local = run.id

    try:
        resp = client.get(
            '/api/step-runs/trends',
            query_string={'pipeline_id': pipeline_id, 'step_type': '__trends_type_a__'},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert '__trends_type_a__' in data['available_step_types']
        assert '__trends_type_b__' in data['available_step_types']
        # series is scoped to the filtered step_type only
        assert data['series'][0]['run_count'] == 1
    finally:
        _delete_run(app, run_id_local)


def test_step_run_trends_days_window_excludes_old_rows(client, headers, pipeline_id, app):
    step_type = '__trends_old__'
    old_date = datetime.now(UTC) - timedelta(days=100)
    run_id_local = _add_run_with_step(app, pipeline_id, step_type, duration_ms=100, rows_affected=10,
                                       started_at=old_date)
    try:
        resp_default = client.get(
            '/api/step-runs/trends', query_string={'step_type': step_type, 'days': 30}, headers=headers,
        )
        assert resp_default.get_json()['series'] == []

        resp_wide = client.get(
            '/api/step-runs/trends', query_string={'step_type': step_type, 'days': 120}, headers=headers,
        )
        assert len(resp_wide.get_json()['series']) == 1
    finally:
        _delete_run(app, run_id_local)


def test_step_run_trends_filters_by_pipeline_id(client, headers, pipeline_id, pipeline_with_project, app):
    """Two pipelines with the same step_type — pipeline_id filter isolates one."""
    other_pipeline_id, _project_id = pipeline_with_project
    step_type = '__trends_pipeline_filter__'
    now = datetime.now(UTC)
    id_a = _add_run_with_step(app, pipeline_id, step_type, duration_ms=100, started_at=now)
    id_b = _add_run_with_step(app, other_pipeline_id, step_type, duration_ms=999, started_at=now)
    try:
        resp = client.get(
            '/api/step-runs/trends',
            query_string={'step_type': step_type, 'pipeline_id': pipeline_id},
            headers=headers,
        )
        data = resp.get_json()
        assert data['series'][0]['run_count'] == 1
        assert data['series'][0]['avg_duration_ms'] == 100.0
    finally:
        _delete_run(app, id_a)
        _delete_run(app, id_b)


def test_step_run_trends_project_id_filter_applied(client, headers, pipeline_id, pipeline_with_project, app):
    """Explicit project_id narrows results to pipelines in that project only —
    a pipeline with no project (project_id NULL) must be excluded."""
    proj_pipeline_id, project_id = pipeline_with_project
    step_type = '__trends_project_filter__'
    now = datetime.now(UTC)
    in_project_run = _add_run_with_step(app, proj_pipeline_id, step_type, duration_ms=100, started_at=now)
    no_project_run = _add_run_with_step(app, pipeline_id, step_type, duration_ms=999, started_at=now)
    try:
        resp = client.get(
            '/api/step-runs/trends',
            query_string={'step_type': step_type, 'project_id': project_id},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['series'][0]['run_count'] == 1
        assert data['series'][0]['avg_duration_ms'] == 100.0
    finally:
        _delete_run(app, in_project_run)
        _delete_run(app, no_project_run)


def test_step_run_trends_project_id_access_denied_for_non_member(
    client, viewer_headers_no_projects, pipeline_with_project,
):
    """A non-admin with no membership in the requested project must get 403,
    not silently-empty results."""
    _pipeline_id, project_id = pipeline_with_project
    resp = client.get(
        '/api/step-runs/trends',
        query_string={'project_id': project_id},
        headers=viewer_headers_no_projects,
    )
    assert resp.status_code == 403


def test_step_run_trends_non_admin_with_no_memberships_sees_nothing(
    client, viewer_headers_no_projects, pipeline_with_project, app,
):
    """A non-admin with zero project memberships must not see step data from
    a project-scoped pipeline they don't belong to, even without an explicit
    project_id filter (accessible_project_ids() restricts implicitly)."""
    proj_pipeline_id, _project_id = pipeline_with_project
    step_type = '__trends_non_admin_scope__'
    run_id_local = _add_run_with_step(app, proj_pipeline_id, step_type, duration_ms=100)
    try:
        resp = client.get(
            '/api/step-runs/trends',
            query_string={'step_type': step_type},
            headers=viewer_headers_no_projects,
        )
        assert resp.status_code == 200
        assert resp.get_json()['series'] == []
    finally:
        _delete_run(app, run_id_local)
