"""Unit tests for flowforge.engine.launcher — dispatch logic."""
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from flowforge.db.models import Pipeline, PipelineRun, db

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_concurrency_slots(monkeypatch):
    """launch_run() reserves a concurrency slot; these tests mock away the
    execution path that would normally release it, so reset between tests.
    Depends on monkeypatch so our post-test reset runs before it reverts
    FLOWFORGE_REDIS_URL — otherwise a real reachable Redis (as in this dev
    environment) would leak slots across tests."""
    from flowforge.engine.concurrency import _reset_for_tests
    _reset_for_tests()
    yield
    _reset_for_tests()


@pytest.fixture
def enabled_pipeline(app):
    with app.app_context():
        p = Pipeline(
            id=str(uuid.uuid4()),
            name='__launcher_test__',
            enabled=True,
        )
        db.session.add(p)
        db.session.commit()
        yield p
        db.session.delete(p)
        db.session.commit()


@pytest.fixture
def disabled_pipeline(app):
    with app.app_context():
        p = Pipeline(
            id=str(uuid.uuid4()),
            name='__launcher_disabled__',
            enabled=False,
        )
        db.session.add(p)
        db.session.commit()
        yield p
        db.session.delete(p)
        db.session.commit()


# ── _use_celery ───────────────────────────────────────────────────────────────

def test_use_celery_false_when_no_redis_url(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    from flowforge.engine.launcher import _use_celery
    assert _use_celery() is False


def test_use_celery_true_when_redis_url_set(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    from flowforge.engine.launcher import _use_celery
    assert _use_celery() is True


def test_use_celery_false_when_empty_string(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', '')
    from flowforge.engine.launcher import _use_celery
    assert _use_celery() is False


# ── launch_run — disabled pipeline ───────────────────────────────────────────

def test_launch_run_disabled_pipeline_returns_400(app, disabled_pipeline, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    with app.app_context():
        p = db.session.get(Pipeline, disabled_pipeline.id)
        from flowforge.engine.launcher import launch_run
        result, status = launch_run(p, 'web_ui', app)
    assert status == 400
    assert 'disabled' in result['error'].lower()


# ── launch_run — thread dispatch ──────────────────────────────────────────────

def test_launch_run_creates_run_record(app, enabled_pipeline, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    with app.app_context():
        p = db.session.get(Pipeline, enabled_pipeline.id)
        with patch('flowforge.engine.launcher._run_in_thread'):
            from flowforge.engine.launcher import launch_run
            result, status = launch_run(p, 'web_ui', app)

    assert status == 202
    assert 'run_id' in result
    assert result['status'] == 'running'
    assert result['pipeline_name'] == '__launcher_test__'

    with app.app_context():
        run = db.session.get(PipelineRun, result['run_id'])
        assert run is not None
        assert run.status == 'running'
        assert run.triggered_by == 'web_ui'
        db.session.delete(run)
        db.session.commit()


def test_launch_run_dispatches_thread(app, enabled_pipeline, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    with app.app_context():
        p = db.session.get(Pipeline, enabled_pipeline.id)
        with patch('threading.Thread') as mock_thread:
            mock_instance = MagicMock()
            mock_thread.return_value = mock_instance
            with patch('flowforge.engine.launcher._run_in_thread'):
                from flowforge.engine.launcher import launch_run
                result, status = launch_run(p, 'scheduler', app)

    assert status == 202
    mock_thread.assert_called_once()
    mock_instance.start.assert_called_once()

    with app.app_context():
        run = db.session.get(PipelineRun, result['run_id'])
        if run:
            db.session.delete(run)
            db.session.commit()


def test_launch_run_returns_429_when_concurrency_exhausted(app, enabled_pipeline, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    with app.app_context():
        p = db.session.get(Pipeline, enabled_pipeline.id)
        with patch('flowforge.engine.launcher.concurrency.try_acquire', return_value=None):
            from flowforge.engine.launcher import launch_run
            result, status = launch_run(p, 'web_ui', app)

    assert status == 429
    assert 'concurrent' in result['error'].lower()
    # No PipelineRun row should be created when the slot couldn't be reserved
    assert 'run_id' not in result


# ── _mark_failed ─────────────────────────────────────────────────────────────

def test_mark_failed_updates_run_status(app, enabled_pipeline):
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=enabled_pipeline.id,
            pipeline_name='__launcher_test__',
            status='running',
            started_at=datetime.now(UTC),
            triggered_by='web_ui',
        )
        db.session.add(run)
        db.session.commit()
        rid = run.id

    with app.app_context():
        from flowforge.engine.launcher import _mark_failed
        _mark_failed(rid, 'Test failure message')

    with app.app_context():
        run = db.session.get(PipelineRun, rid)
        assert run.status == 'failed'
        assert run.error_message == 'Test failure message'
        assert run.finished_at is not None
        db.session.delete(run)
        db.session.commit()


def test_mark_failed_nonexistent_run_does_not_raise(app):
    with app.app_context():
        from flowforge.engine.launcher import _mark_failed
        _mark_failed('00000000-0000-0000-0000-000000000099', 'ghost run')
