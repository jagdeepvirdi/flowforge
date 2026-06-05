"""Tests for flowforge/api/routes/runs.py — _check_anomaly, project_id filter,
anomalies endpoint, diff endpoint, cancel, download."""
import uuid
from datetime import UTC, datetime

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
