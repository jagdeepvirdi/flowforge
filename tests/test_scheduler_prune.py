"""Unit tests for scheduler helper functions.

Covers: _register_cleanup_job, _register_sync_job, _cleanup_job,
        _prune_old_runs, _prune_old_audit_logs, _prune_token_blocklist,
        _sync_db_job, _run_pipeline_job.
"""
import os
from unittest.mock import MagicMock, call, patch

import pytest


def _make_mock_app():
    app = MagicMock()
    app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    app.app_context.return_value.__exit__ = MagicMock(return_value=False)
    return app


def _mock_db_session():
    """Return a mock db with a chainable session.query(...).filter(...).delete() setup."""
    mock_db = MagicMock()
    query = MagicMock()
    mock_db.session.query.return_value = query
    query.filter.return_value = query
    query.delete.return_value = 3
    return mock_db


# ── _register_cleanup_job ──────────────────────────────────────────────────────

def test_register_cleanup_job_schedules_daily():
    import flowforge.engine.scheduler as sched_mod
    mock_sched = MagicMock()
    sched_mod._scheduler = mock_sched
    sched_mod._register_cleanup_job()
    mock_sched.add_job.assert_called_once()
    kwargs = mock_sched.add_job.call_args.kwargs
    assert kwargs['trigger'] == 'cron'
    assert kwargs['hour'] == 2
    assert kwargs['id'] == 'output_cleanup'


# ── _register_sync_job ─────────────────────────────────────────────────────────

def test_register_sync_job_uses_interval():
    import flowforge.engine.scheduler as sched_mod
    mock_sched = MagicMock()
    sched_mod._scheduler = mock_sched
    sched_mod._register_sync_job()
    mock_sched.add_job.assert_called_once()
    kwargs = mock_sched.add_job.call_args.kwargs
    assert kwargs['trigger'] == 'interval'
    assert kwargs['id'] == '_pipeline_sync'


# ── _cleanup_job ───────────────────────────────────────────────────────────────

def test_cleanup_job_calls_all_helpers():
    import flowforge.engine.scheduler as sched_mod
    with patch.object(sched_mod, '_prune_token_blocklist') as mock_tb, \
         patch.object(sched_mod, '_prune_old_runs') as mock_runs, \
         patch.object(sched_mod, '_prune_old_audit_logs') as mock_audit, \
         patch('flowforge.engine.cleanup.cleanup_output_files') as mock_cleanup:
        sched_mod._cleanup_job()
    mock_cleanup.assert_called_once()
    mock_tb.assert_called_once()
    mock_runs.assert_called_once()
    mock_audit.assert_called_once()


# ── _prune_old_runs ────────────────────────────────────────────────────────────

def test_prune_old_runs_no_op_when_app_is_none():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = None
    try:
        sched_mod._prune_old_runs()  # must not raise
    finally:
        sched_mod._app = original


def test_prune_old_runs_no_op_when_retention_zero():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    try:
        with patch.dict(os.environ, {'FLOWFORGE_RUN_RETENTION_DAYS': '0'}):
            sched_mod._prune_old_runs()  # must not create app context
        sched_mod._app.app_context.assert_not_called()
    finally:
        sched_mod._app = original


def test_prune_old_runs_deletes_and_commits():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    mock_db = _mock_db_session()
    try:
        with patch.dict(os.environ, {'FLOWFORGE_RUN_RETENTION_DAYS': '30'}), \
             patch('flowforge.db.models.db', mock_db):
            sched_mod._prune_old_runs()
        mock_db.session.query.assert_called_once()
        mock_db.session.commit.assert_called_once()
    finally:
        sched_mod._app = original


def test_prune_old_runs_swallows_exception():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    mock_app = _make_mock_app()
    mock_app.app_context.return_value.__enter__.side_effect = Exception('db error')
    sched_mod._app = mock_app
    try:
        sched_mod._prune_old_runs()  # must not raise
    finally:
        sched_mod._app = original


# ── _prune_old_audit_logs ──────────────────────────────────────────────────────

def test_prune_old_audit_logs_no_op_when_app_is_none():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = None
    try:
        sched_mod._prune_old_audit_logs()
    finally:
        sched_mod._app = original


def test_prune_old_audit_logs_no_op_when_retention_zero():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    try:
        env = {'FLOWFORGE_AUDIT_RETENTION_DAYS': '0', 'FLOWFORGE_RUN_RETENTION_DAYS': '0'}
        with patch.dict(os.environ, env):
            sched_mod._prune_old_audit_logs()
        sched_mod._app.app_context.assert_not_called()
    finally:
        sched_mod._app = original


def test_prune_old_audit_logs_deletes_and_commits():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    mock_db = _mock_db_session()
    try:
        with patch.dict(os.environ, {'FLOWFORGE_AUDIT_RETENTION_DAYS': '30'}), \
             patch('flowforge.db.models.db', mock_db):
            sched_mod._prune_old_audit_logs()
        mock_db.session.commit.assert_called_once()
    finally:
        sched_mod._app = original


def test_prune_old_audit_logs_swallows_exception():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    mock_app = _make_mock_app()
    mock_app.app_context.return_value.__enter__.side_effect = Exception('oops')
    sched_mod._app = mock_app
    try:
        sched_mod._prune_old_audit_logs()
    finally:
        sched_mod._app = original


def test_prune_old_audit_logs_defaults_to_run_retention():
    """Falls back to FLOWFORGE_RUN_RETENTION_DAYS when AUDIT_RETENTION_DAYS is absent."""
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    mock_db = _mock_db_session()
    env = {'FLOWFORGE_RUN_RETENTION_DAYS': '60'}
    env_clean = {k: v for k, v in os.environ.items()
                 if k not in ('FLOWFORGE_AUDIT_RETENTION_DAYS',)}
    try:
        with patch.dict(os.environ, {**env_clean, **env}, clear=True), \
             patch('flowforge.db.models.db', mock_db):
            sched_mod._prune_old_audit_logs()
        mock_db.session.commit.assert_called_once()
    finally:
        sched_mod._app = original


# ── _prune_token_blocklist ─────────────────────────────────────────────────────

def test_prune_token_blocklist_no_op_when_app_is_none():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = None
    try:
        sched_mod._prune_token_blocklist()
    finally:
        sched_mod._app = original


def test_prune_token_blocklist_deletes_expired():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    mock_db = _mock_db_session()
    try:
        with patch('flowforge.db.models.db', mock_db):
            sched_mod._prune_token_blocklist()
        mock_db.session.commit.assert_called_once()
    finally:
        sched_mod._app = original


def test_prune_token_blocklist_swallows_exception():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    mock_app = _make_mock_app()
    mock_app.app_context.return_value.__enter__.side_effect = Exception('crash')
    sched_mod._app = mock_app
    try:
        sched_mod._prune_token_blocklist()
    finally:
        sched_mod._app = original


# ── _sync_db_job ───────────────────────────────────────────────────────────────

def test_sync_db_job_no_op_when_app_is_none():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = None
    try:
        sched_mod._sync_db_job()  # must not raise
    finally:
        sched_mod._app = original


def test_sync_db_job_calls_sync_pipeline_jobs():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    try:
        with patch.object(sched_mod, '_sync_pipeline_jobs') as mock_sync:
            sched_mod._sync_db_job()
        mock_sync.assert_called_once()
    finally:
        sched_mod._app = original


def test_sync_db_job_swallows_exception():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    try:
        with patch.object(sched_mod, '_sync_pipeline_jobs', side_effect=Exception('db down')):
            sched_mod._sync_db_job()  # must not raise
    finally:
        sched_mod._app = original


# ── _run_pipeline_job ──────────────────────────────────────────────────────────

def test_run_pipeline_job_no_op_when_app_is_none():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = None
    try:
        sched_mod._run_pipeline_job('pid', 'My Pipeline')  # must not raise
    finally:
        sched_mod._app = original


def test_run_pipeline_job_pipeline_not_found():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    mock_db = MagicMock()
    mock_db.session.get.return_value = None
    try:
        with patch('flowforge.db.models.db', mock_db):
            sched_mod._run_pipeline_job('missing-id', 'Ghost Pipeline')  # must not raise
    finally:
        sched_mod._app = original


def test_run_pipeline_job_calls_launch_run():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    mock_app = _make_mock_app()
    sched_mod._app = mock_app
    mock_pipeline = MagicMock()
    mock_db = MagicMock()
    mock_db.session.get.return_value = mock_pipeline
    try:
        with patch('flowforge.db.models.db', mock_db), \
             patch('flowforge.engine.launcher.launch_run', return_value=({'run_id': 'r1'}, 202)) as mock_launch:
            sched_mod._run_pipeline_job('pid', 'My Pipeline')
        mock_launch.assert_called_once_with(mock_pipeline, triggered_by='scheduler', app=mock_app)
    finally:
        sched_mod._app = original


def test_run_pipeline_job_logs_warning_on_non_202():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    mock_pipeline = MagicMock()
    mock_db = MagicMock()
    mock_db.session.get.return_value = mock_pipeline
    try:
        with patch('flowforge.db.models.db', mock_db), \
             patch('flowforge.engine.launcher.launch_run',
                   return_value=({'error': 'already running'}, 409)):
            sched_mod._run_pipeline_job('pid', 'My Pipeline')  # must not raise
    finally:
        sched_mod._app = original


def test_run_pipeline_job_swallows_exception():
    import flowforge.engine.scheduler as sched_mod
    original = sched_mod._app
    sched_mod._app = _make_mock_app()
    mock_db = MagicMock()
    mock_db.session.get.side_effect = Exception('session error')
    try:
        with patch('flowforge.db.models.db', mock_db):
            sched_mod._run_pipeline_job('pid', 'Pipeline')  # must not raise
    finally:
        sched_mod._app = original
