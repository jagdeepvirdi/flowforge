"""Extended tests for run history endpoints — anomalies, cancel, download, filters."""
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from flowforge.db.models import Pipeline, PipelineRun, StepRun, db


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pipeline_id(client, headers):
    resp = client.post('/api/pipelines', json={'name': '__runs_ext__', 'enabled': True}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/pipelines/{pid}', headers=headers)


@pytest.fixture
def run_id(app, pipeline_id):
    """Insert a completed run directly."""
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            pipeline_name='__runs_ext__',
            status='success',
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            duration_ms=1234,
            triggered_by='web_ui',
        )
        db.session.add(run)
        db.session.commit()
        yield run.id
        db.session.delete(run)
        db.session.commit()


@pytest.fixture
def running_run_id(app, pipeline_id):
    """Insert a run with status='running'."""
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            pipeline_name='__runs_ext__',
            status='running',
            started_at=datetime.now(timezone.utc),
            triggered_by='scheduler',
        )
        db.session.add(run)
        db.session.commit()
        yield run.id
        try:
            r = db.session.get(PipelineRun, run.id)
            if r:
                db.session.delete(r)
                db.session.commit()
        except Exception:
            pass


# ── GET /runs (extended filters) ──────────────────────────────────────────────

def test_list_runs_filter_by_pipeline_id(client, headers, pipeline_id, run_id):
    resp = client.get(f'/api/runs?pipeline_id={pipeline_id}', headers=headers)
    assert resp.status_code == 200
    runs = resp.get_json()
    assert all(r['pipeline_id'] == pipeline_id for r in runs)


def test_list_runs_with_offset(client, headers):
    resp = client.get('/api/runs?limit=10&offset=0', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_list_runs_with_project_id_filter(client, headers):
    """project_id filter joins Pipeline table — should return 200 without error."""
    resp = client.get(
        '/api/runs?project_id=00000000-0000-0000-0000-000000000000',
        headers=headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_list_runs_requires_auth(client):
    resp = client.get('/api/runs')
    assert resp.status_code == 401


# ── GET /runs/:id ─────────────────────────────────────────────────────────────

def test_get_run_by_id(client, headers, run_id):
    resp = client.get(f'/api/runs/{run_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == run_id
    assert data['status'] == 'success'
    assert 'step_runs' in data


def test_get_run_includes_step_runs_list(client, headers, run_id):
    resp = client.get(f'/api/runs/{run_id}', headers=headers)
    data = resp.get_json()
    assert isinstance(data['step_runs'], list)


def test_get_run_not_found(client, headers):
    resp = client.get('/api/runs/00000000-0000-0000-0000-000000000001', headers=headers)
    assert resp.status_code == 404


def test_get_run_requires_auth(client, run_id):
    resp = client.get(f'/api/runs/{run_id}')
    assert resp.status_code == 401


# ── GET /runs/:id/anomalies ───────────────────────────────────────────────────

def test_get_anomalies_returns_list(client, headers, run_id):
    resp = client.get(f'/api/runs/{run_id}/anomalies', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_get_anomalies_empty_for_run_without_steps(client, headers, run_id):
    resp = client.get(f'/api/runs/{run_id}/anomalies', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_anomalies_not_found(client, headers):
    resp = client.get(
        '/api/runs/00000000-0000-0000-0000-000000000002/anomalies',
        headers=headers,
    )
    assert resp.status_code == 404


def test_get_anomalies_requires_auth(client, run_id):
    resp = client.get(f'/api/runs/{run_id}/anomalies')
    assert resp.status_code == 401


def test_get_anomalies_for_run_with_null_pipeline(client, headers, app):
    """Run where pipeline_id is NULL returns empty anomaly list (not an error)."""
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=None,
            pipeline_name='Deleted Pipeline',
            status='success',
            started_at=datetime.now(timezone.utc),
            triggered_by='web_ui',
        )
        db.session.add(run)
        db.session.commit()
        rid = run.id

    resp = client.get(f'/api/runs/{rid}/anomalies', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []

    with app.app_context():
        r = db.session.get(PipelineRun, rid)
        if r:
            db.session.delete(r)
            db.session.commit()


# ── POST /runs/:id/cancel ─────────────────────────────────────────────────────

def test_cancel_running_run(client, headers, running_run_id):
    resp = client.post(f'/api/runs/{running_run_id}/cancel', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['run_id'] == running_run_id


def test_cancel_already_completed_run_returns_409(client, headers, run_id):
    resp = client.post(f'/api/runs/{run_id}/cancel', headers=headers)
    assert resp.status_code == 409


def test_cancel_nonexistent_run_returns_404(client, headers):
    resp = client.post(
        '/api/runs/00000000-0000-0000-0000-000000000003/cancel',
        headers=headers,
    )
    assert resp.status_code == 404


def test_cancel_run_requires_auth(client, running_run_id):
    resp = client.post(f'/api/runs/{running_run_id}/cancel')
    assert resp.status_code == 401


# ── GET /step-runs/:id/download ───────────────────────────────────────────────

def test_download_step_output_not_found(client, headers):
    resp = client.get(
        '/api/step-runs/00000000-0000-0000-0000-000000000004/download',
        headers=headers,
    )
    assert resp.status_code == 404


def test_download_step_output_no_output_path(client, headers, app, run_id):
    """Step run with no output_path returns 404."""
    with app.app_context():
        step = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='no_output',
            step_type='db_query',
            step_order=1,
            status='success',
            started_at=datetime.now(timezone.utc),
            output_path=None,
        )
        db.session.add(step)
        db.session.commit()
        sid = step.id

    resp = client.get(f'/api/step-runs/{sid}/download', headers=headers)
    assert resp.status_code == 404

    with app.app_context():
        s = db.session.get(StepRun, sid)
        if s:
            db.session.delete(s)
            db.session.commit()


def test_download_step_output_path_traversal_blocked(client, headers, app, run_id):
    """Output path outside FLOWFORGE_OUTPUT_DIR is rejected with 403."""
    with app.app_context():
        step = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='bad_path',
            step_type='report',
            step_order=1,
            status='success',
            started_at=datetime.now(timezone.utc),
            output_path='/etc/passwd',
        )
        db.session.add(step)
        db.session.commit()
        sid = step.id

    resp = client.get(f'/api/step-runs/{sid}/download', headers=headers)
    assert resp.status_code == 403

    with app.app_context():
        s = db.session.get(StepRun, sid)
        if s:
            db.session.delete(s)
            db.session.commit()


def test_download_step_output_file_serves_content(client, headers, app, run_id, tmp_path, monkeypatch):
    """Step run whose output_path exists on disk and is inside FLOWFORGE_OUTPUT_DIR → 200."""
    monkeypatch.setenv('FLOWFORGE_OUTPUT_DIR', str(tmp_path))
    tmp_file = tmp_path / f'report_{uuid.uuid4().hex}.txt'
    tmp_file.write_text('hello test report content')

    with app.app_context():
        step = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='real_output',
            step_type='report',
            step_order=1,
            status='success',
            started_at=datetime.now(timezone.utc),
            output_path=str(tmp_file),
        )
        db.session.add(step)
        db.session.commit()
        sid = step.id

    try:
        resp = client.get(f'/api/step-runs/{sid}/download', headers=headers)
        assert resp.status_code == 200
    finally:
        with app.app_context():
            s = db.session.get(StepRun, sid)
            if s:
                db.session.delete(s)
                db.session.commit()


def test_download_step_output_requires_auth(client, app, run_id):
    with app.app_context():
        step = StepRun(
            id=str(uuid.uuid4()),
            pipeline_run_id=run_id,
            step_name='auth_check',
            step_type='report',
            step_order=1,
            status='success',
            started_at=datetime.now(timezone.utc),
            output_path=None,
        )
        db.session.add(step)
        db.session.commit()
        sid = step.id

    resp = client.get(f'/api/step-runs/{sid}/download')
    assert resp.status_code == 401

    with app.app_context():
        s = db.session.get(StepRun, sid)
        if s:
            db.session.delete(s)
            db.session.commit()
