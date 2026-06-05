"""Tests for the _cancel_stuck_runs inner loop in engine/shutdown.py.

Covers the previously-uncovered lines 141-155: the path where stuck runs
actually exist and must be marked 'cancelled', the SQLAlchemyError branch,
and the outer Exception branch.
"""
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_shutdown():
    import flowforge.engine.shutdown as sd
    sd._shutdown_event.clear()
    sd._active_runs.clear()
    sd._app = None
    yield
    sd._shutdown_event.clear()
    sd._active_runs.clear()
    sd._app = None


def _mock_app():
    app = MagicMock()
    app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    app.app_context.return_value.__exit__ = MagicMock(return_value=False)
    return app


# ── runs with started_at set ──────────────────────────────────────────────────

def test_cancel_stuck_runs_marks_runs_cancelled():
    import flowforge.engine.shutdown as sd

    run1 = MagicMock()
    run1.started_at = datetime(2026, 1, 1, tzinfo=UTC)
    run2 = MagicMock()
    run2.started_at = None  # edge: no duration_ms calculation

    mock_db = MagicMock()
    mock_db.session.query.return_value.filter_by.return_value.all.return_value = [run1, run2]

    sd._app = _mock_app()
    with patch('flowforge.db.models.db', mock_db):
        sd._cancel_stuck_runs()

    assert run1.status == 'cancelled'
    assert run1.error_message == 'Process shutdown before run completed'
    assert run1.finished_at is not None
    assert run1.duration_ms is not None

    assert run2.status == 'cancelled'
    assert run2.error_message == 'Process shutdown before run completed'
    mock_db.session.commit.assert_called_once()


def test_cancel_stuck_runs_no_runs_returns_early():
    import flowforge.engine.shutdown as sd

    mock_db = MagicMock()
    mock_db.session.query.return_value.filter_by.return_value.all.return_value = []

    sd._app = _mock_app()
    with patch('flowforge.db.models.db', mock_db):
        sd._cancel_stuck_runs()

    mock_db.session.commit.assert_not_called()


# ── SQLAlchemyError branch (lines 152-153) ────────────────────────────────────

def test_cancel_stuck_runs_swallows_sqlalchemy_error():
    from sqlalchemy.exc import SQLAlchemyError
    import flowforge.engine.shutdown as sd

    mock_db = MagicMock()
    mock_db.session.query.return_value.filter_by.return_value.all.side_effect = SQLAlchemyError('db down')

    sd._app = _mock_app()
    with patch('flowforge.db.models.db', mock_db):
        sd._cancel_stuck_runs()  # must not raise


# ── outer Exception branch (lines 154-155) ───────────────────────────────────

def test_cancel_stuck_runs_swallows_app_context_exception():
    import flowforge.engine.shutdown as sd

    bad_app = MagicMock()
    bad_app.app_context.return_value.__enter__.side_effect = Exception('app crashed')
    bad_app.app_context.return_value.__exit__ = MagicMock(return_value=False)
    sd._app = bad_app
    sd._cancel_stuck_runs()  # must not raise


# ── duration_ms calculation ────────────────────────────────────────────────────

def test_duration_ms_computed_from_started_at():
    import flowforge.engine.shutdown as sd

    started = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    run = MagicMock()
    run.started_at = started

    mock_db = MagicMock()
    mock_db.session.query.return_value.filter_by.return_value.all.return_value = [run]

    sd._app = _mock_app()
    with patch('flowforge.db.models.db', mock_db):
        sd._cancel_stuck_runs()

    assert isinstance(run.duration_ms, int)
    assert run.duration_ms >= 0
