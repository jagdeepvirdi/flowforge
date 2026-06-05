"""Extended tests for engine/launcher.py — covers Celery dispatch path,
_run_in_thread load-failure branch, and _mark_failed exception path
(lines 34-36, 67-70, 96-97).
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from flowforge.db.models import Pipeline, PipelineRun, db

# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def pipeline(app):
    with app.app_context():
        p = Pipeline(id=str(uuid.uuid4()), name='__ext_launcher__', enabled=True)
        db.session.add(p)
        db.session.commit()
        yield p
        db.session.delete(db.session.get(Pipeline, p.id))
        db.session.commit()


# ── Celery dispatch path (lines 34-36) ────────────────────────────────────────

def test_launch_run_celery_path_calls_task_delay(app, pipeline, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')

    mock_task = MagicMock()
    with app.app_context():
        p = db.session.get(Pipeline, pipeline.id)
        with patch.dict('sys.modules', {'flowforge.tasks': MagicMock(run_pipeline_task=mock_task)}), \
             patch('flowforge.engine.launcher._use_celery', return_value=True):
            from flowforge.engine.launcher import launch_run
            result, status = launch_run(p, 'scheduler', app)

    assert status == 202
    mock_task.delay.assert_called_once()

    with app.app_context():
        run = db.session.get(PipelineRun, result['run_id'])
        if run:
            db.session.delete(run)
            db.session.commit()


# ── _run_in_thread load-failure branch (lines 67-70) ──────────────────────────

def test_run_in_thread_load_failure_marks_run_failed(app, pipeline):
    """When load_pipeline raises, the run must be marked 'failed' via _mark_failed."""
    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline.id,
            pipeline_name='__ext_launcher__',
            status='running',
            started_at=datetime.now(UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    from flowforge.engine.launcher import _run_in_thread

    with patch('flowforge.engine.loader.load_pipeline', side_effect=Exception('schema missing')):
        _run_in_thread(app, pipeline.id, '__ext_launcher__', 'test', run_id)

    with app.app_context():
        updated = db.session.get(PipelineRun, run_id)
        assert updated.status == 'failed'
        assert 'schema missing' in updated.error_message
        db.session.delete(updated)
        db.session.commit()


# ── _mark_failed exception path (lines 96-97) ─────────────────────────────────

def test_mark_failed_swallows_db_exception(app):
    """If the DB session raises while marking a run failed, the exception is swallowed."""
    from flowforge.engine.launcher import _mark_failed

    with app.app_context():
        with patch('flowforge.db.models.db') as mock_db:
            mock_db.session.get.side_effect = Exception('db connection lost')
            _mark_failed('fake-run-id', 'Test failure')  # must not raise
