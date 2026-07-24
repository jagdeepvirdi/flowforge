"""Unit tests for the APScheduler integration (engine/scheduler.py).

Exercises job sync logic and jobstore configuration without starting a real
scheduler or connecting to a real database.
"""
from unittest.mock import MagicMock, patch

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_pipeline(pid, name, schedule, enabled=True):
    p = MagicMock()
    p.id = pid
    p.name = name
    p.schedule = schedule
    p.enabled = enabled
    return p


def _make_scheduler(existing_job_ids=None):
    """Return a mock APScheduler with a pre-populated jobs list."""
    sched = MagicMock()
    jobs = [MagicMock(id=jid) for jid in (existing_job_ids or [])]
    sched.get_jobs.return_value = jobs
    return sched


def _run_sync(pipelines, existing_job_ids=None):
    """Call _sync_pipeline_jobs with mocked DB and scheduler."""
    import flowforge.engine.scheduler as sched_mod

    mock_sched = _make_scheduler(existing_job_ids)
    sched_mod._scheduler = mock_sched

    mock_db = MagicMock()
    mock_db.session.query.return_value.filter_by.return_value.all.return_value = pipelines

    # _sync_pipeline_jobs does `from flowforge.db.models import Pipeline, db` locally,
    # so patch at the source module, not the scheduler module.
    with patch('flowforge.db.models.db', mock_db), \
         patch('flowforge.engine.scheduler.db', mock_db, create=True):
        sched_mod._sync_pipeline_jobs()

    return mock_sched


# ── _sync_pipeline_jobs — job registration ────────────────────────────────────

def test_sync_adds_job_for_scheduled_pipeline():
    pipelines = [_make_pipeline('pid1', 'Daily Report', '0 8 * * *')]
    sched = _run_sync(pipelines)
    sched.add_job.assert_called_once()
    kwargs = sched.add_job.call_args[1]
    assert kwargs['id'] == 'pipeline_pid1'


def test_sync_uses_replace_existing():
    pipelines = [_make_pipeline('pid1', 'Daily Report', '0 8 * * *')]
    sched = _run_sync(pipelines)
    kwargs = sched.add_job.call_args[1]
    assert kwargs['replace_existing'] is True


def test_sync_sets_misfire_grace_time():
    pipelines = [_make_pipeline('pid1', 'Daily Report', '0 8 * * *')]
    sched = _run_sync(pipelines)
    kwargs = sched.add_job.call_args[1]
    assert kwargs['misfire_grace_time'] == 300


def test_sync_parses_cron_fields_correctly():
    pipelines = [_make_pipeline('pid1', 'Report', '30 9 15 * 1')]
    sched = _run_sync(pipelines)
    kwargs = sched.add_job.call_args[1]
    assert kwargs['minute'] == '30'
    assert kwargs['hour'] == '9'
    assert kwargs['day'] == '15'
    assert kwargs['month'] == '*'
    assert kwargs['day_of_week'] == '1'


def test_sync_skips_pipeline_without_schedule():
    pipelines = [_make_pipeline('pid1', 'No Schedule', None)]
    sched = _run_sync(pipelines)
    sched.add_job.assert_not_called()


def test_sync_skips_pipeline_with_empty_schedule():
    pipelines = [_make_pipeline('pid1', 'Empty Schedule', '')]
    sched = _run_sync(pipelines)
    sched.add_job.assert_not_called()


def test_sync_registers_multiple_pipelines():
    pipelines = [
        _make_pipeline('pid1', 'Daily', '0 8 * * *'),
        _make_pipeline('pid2', 'Weekly', '0 9 * * 1'),
        _make_pipeline('pid3', 'Monthly', '0 6 1 * *'),
    ]
    sched = _run_sync(pipelines)
    assert sched.add_job.call_count == 3


def test_sync_job_id_prefixed_with_pipeline():
    pipelines = [_make_pipeline('abc-123', 'Test', '0 8 * * *')]
    sched = _run_sync(pipelines)
    kwargs = sched.add_job.call_args[1]
    assert kwargs['id'] == 'pipeline_abc-123'


def test_sync_trigger_is_cron():
    pipelines = [_make_pipeline('pid1', 'Daily', '0 8 * * *')]
    sched = _run_sync(pipelines)
    args = sched.add_job.call_args
    assert args[1]['trigger'] == 'cron' or args[0][1] == 'cron'


def test_sync_passes_pipeline_id_and_name_as_args():
    pipelines = [_make_pipeline('pid1', 'My Report', '0 8 * * *')]
    sched = _run_sync(pipelines)
    kwargs = sched.add_job.call_args[1]
    assert 'pid1' in kwargs['args']
    assert 'My Report' in kwargs['args']


# ── _sync_pipeline_jobs — stale job removal ───────────────────────────────────

def test_sync_removes_stale_job():
    """A job with no matching active pipeline is removed."""
    pipelines = []  # no active pipelines
    sched = _run_sync(pipelines, existing_job_ids=['pipeline_old'])
    sched.remove_job.assert_called_once_with('pipeline_old')


def test_sync_removes_only_stale_jobs():
    """Only jobs whose pipeline is gone are removed; active ones stay."""
    pipelines = [_make_pipeline('pid1', 'Active', '0 8 * * *')]
    existing = ['pipeline_pid1', 'pipeline_gone']
    sched = _run_sync(pipelines, existing_job_ids=existing)
    sched.remove_job.assert_called_once_with('pipeline_gone')


def test_sync_no_removal_when_all_active():
    pipelines = [_make_pipeline('pid1', 'Active', '0 8 * * *')]
    sched = _run_sync(pipelines, existing_job_ids=['pipeline_pid1'])
    sched.remove_job.assert_not_called()


def test_sync_does_not_remove_non_pipeline_jobs():
    """Internal jobs like _pipeline_sync and output_cleanup are not removed."""
    pipelines = []
    sched = _run_sync(pipelines, existing_job_ids=['output_cleanup', '_pipeline_sync'])
    sched.remove_job.assert_not_called()


# ── _sync_pipeline_jobs — invalid cron handling ────────────────────────────────

def test_sync_skips_invalid_cron_too_few_parts():
    """A cron expression with fewer than 5 fields is skipped gracefully."""
    pipelines = [_make_pipeline('pid1', 'Bad Cron', '0 8 * *')]  # only 4 parts
    sched = _run_sync(pipelines)
    sched.add_job.assert_not_called()


def test_sync_skips_invalid_cron_too_many_parts():
    pipelines = [_make_pipeline('pid1', 'Bad Cron', '0 8 * * * *')]  # 6 parts
    sched = _run_sync(pipelines)
    sched.add_job.assert_not_called()


def test_sync_continues_after_one_invalid_pipeline():
    """Scheduler continues registering valid pipelines after an invalid one."""
    pipelines = [
        _make_pipeline('bad', 'Bad Cron', '0 8 * *'),   # invalid
        _make_pipeline('good', 'Good Cron', '0 9 * * *'),  # valid
    ]
    sched = _run_sync(pipelines)
    assert sched.add_job.call_count == 1
    kwargs = sched.add_job.call_args[1]
    assert kwargs['id'] == 'pipeline_good'


def test_sync_handles_add_job_exception_gracefully():
    """An exception from scheduler.add_job does not crash the sync."""
    import flowforge.engine.scheduler as sched_mod

    mock_sched = _make_scheduler()
    mock_sched.add_job.side_effect = Exception('scheduler error')
    sched_mod._scheduler = mock_sched

    pipelines = [_make_pipeline('pid1', 'Report', '0 8 * * *')]
    mock_db = MagicMock()
    mock_db.session.query.return_value.filter_by.return_value.all.return_value = pipelines

    with patch('flowforge.db.models.db', mock_db):
        sched_mod._sync_pipeline_jobs()   # must not raise


# ── Jobstore configuration ────────────────────────────────────────────────────

def test_start_scheduler_uses_postgres_jobstore_when_db_url_set():
    """SQLAlchemyJobStore is configured when FLOWFORGE_DB_URL is present."""
    from flowforge.engine.scheduler import start_scheduler

    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    captured = {}

    def fake_blocking_scheduler(jobstores=None, **kwargs):
        captured['jobstores'] = jobstores or {}
        sched = MagicMock()
        sched.start.side_effect = KeyboardInterrupt
        return sched

    with patch.dict('os.environ', {'FLOWFORGE_DB_URL': 'postgresql://u:p@db/flowforge'}), \
         patch('flowforge.engine.scheduler.BlockingScheduler', side_effect=fake_blocking_scheduler), \
         patch('flowforge.engine.scheduler.SQLAlchemyJobStore') as _mock_store, \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'):
        try:
            start_scheduler(mock_app)
        except (KeyboardInterrupt, SystemExit):
            pass

    assert 'default' in captured['jobstores']


def test_start_scheduler_uses_memory_jobstore_when_no_db_url():
    """Falls back to empty jobstores (in-memory) when FLOWFORGE_DB_URL is absent."""
    from flowforge.engine.scheduler import start_scheduler

    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    captured = {}

    def fake_blocking_scheduler(jobstores=None, **kwargs):
        captured['jobstores'] = jobstores or {}
        sched = MagicMock()
        sched.start.side_effect = KeyboardInterrupt
        return sched

    env = {k: v for k, v in __import__('os').environ.items() if k != 'FLOWFORGE_DB_URL'}
    with patch.dict('os.environ', env, clear=True), \
         patch('flowforge.engine.scheduler.BlockingScheduler', side_effect=fake_blocking_scheduler), \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'):
        try:
            start_scheduler(mock_app)
        except (KeyboardInterrupt, SystemExit):
            pass

    assert captured['jobstores'] == {}


def test_start_scheduler_logs_postgres_jobstore(caplog):
    """A log message confirms the PostgreSQL jobstore is active."""
    import logging

    from flowforge.engine.scheduler import start_scheduler

    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    def fake_sched(**kwargs):
        s = MagicMock()
        s.start.side_effect = KeyboardInterrupt
        return s

    with patch.dict('os.environ', {'FLOWFORGE_DB_URL': 'postgresql://u:p@myhost/flowforge'}), \
         patch('flowforge.engine.scheduler.BlockingScheduler', side_effect=fake_sched), \
         patch('flowforge.engine.scheduler.SQLAlchemyJobStore'), \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'), \
         caplog.at_level(logging.INFO, logger='flowforge.engine.scheduler'):
        try:
            start_scheduler(mock_app)
        except (KeyboardInterrupt, SystemExit):
            pass

    assert any('PostgreSQL' in m or 'jobstore' in m.lower() for m in caplog.messages)


def test_start_scheduler_logs_warning_when_no_db_url(caplog):
    """A WARNING is emitted when falling back to in-memory jobstore."""
    import logging

    from flowforge.engine.scheduler import start_scheduler

    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    def fake_sched(**kwargs):
        s = MagicMock()
        s.start.side_effect = KeyboardInterrupt
        return s

    env = {k: v for k, v in __import__('os').environ.items() if k != 'FLOWFORGE_DB_URL'}
    with patch.dict('os.environ', env, clear=True), \
         patch('flowforge.engine.scheduler.BlockingScheduler', side_effect=fake_sched), \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'), \
         caplog.at_level(logging.WARNING, logger='flowforge.engine.scheduler'):
        try:
            start_scheduler(mock_app)
        except (KeyboardInterrupt, SystemExit):
            pass

    assert any('in-memory' in m.lower() or 'restart' in m.lower() for m in caplog.messages)


# ── Credential safety ─────────────────────────────────────────────────────────

def test_postgres_url_credentials_not_logged(caplog):
    """Database credentials in FLOWFORGE_DB_URL must not appear in log output."""
    import logging

    from flowforge.engine.scheduler import start_scheduler

    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    def fake_sched(**kwargs):
        s = MagicMock()
        s.start.side_effect = KeyboardInterrupt
        return s

    secret_password = 'sup3r_s3cr3t_p@ssword'
    db_url = f'postgresql://flowforge:{secret_password}@db.prod.internal/flowforge'

    with patch.dict('os.environ', {'FLOWFORGE_DB_URL': db_url}), \
         patch('flowforge.engine.scheduler.BlockingScheduler', side_effect=fake_sched), \
         patch('flowforge.engine.scheduler.SQLAlchemyJobStore'), \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'), \
         caplog.at_level(logging.DEBUG, logger='flowforge.engine.scheduler'):
        try:
            start_scheduler(mock_app)
        except (KeyboardInterrupt, SystemExit):
            pass

    for msg in caplog.messages:
        assert secret_password not in msg, f"Password leaked in log: {msg}"


# ── HA leader election wiring ──────────────────────────────────────────────

def test_start_scheduler_skips_leader_election_without_redis_url(caplog):
    """No FLOWFORGE_REDIS_URL: _scheduler.start() is called directly, no election."""
    import logging

    from flowforge.engine.scheduler import start_scheduler

    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    def fake_sched(**kwargs):
        s = MagicMock()
        s.start.side_effect = KeyboardInterrupt
        return s

    env = {k: v for k, v in __import__('os').environ.items()
           if k not in ('FLOWFORGE_DB_URL', 'FLOWFORGE_REDIS_URL')}
    with patch.dict('os.environ', env, clear=True), \
         patch('flowforge.engine.scheduler.BlockingScheduler', side_effect=fake_sched), \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'), \
         patch('flowforge.engine.leader.run_with_leadership') as mock_run_with_leadership, \
         caplog.at_level(logging.WARNING, logger='flowforge.engine.scheduler'):
        try:
            start_scheduler(mock_app)
        except (KeyboardInterrupt, SystemExit):
            pass

    mock_run_with_leadership.assert_not_called()
    assert any('no leader election' in m.lower() for m in caplog.messages)


def test_start_scheduler_uses_leader_election_with_redis_url(caplog):
    """FLOWFORGE_REDIS_URL set: the scheduler start is routed through run_with_leadership."""
    import logging

    from flowforge.engine.scheduler import start_scheduler

    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    def fake_sched(**kwargs):
        s = MagicMock()
        s.start.side_effect = KeyboardInterrupt
        return s

    with patch.dict('os.environ', {'FLOWFORGE_REDIS_URL': 'redis://localhost:6379/0'}), \
         patch('flowforge.engine.scheduler.BlockingScheduler', side_effect=fake_sched), \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'), \
         patch('flowforge.engine.leader.run_with_leadership') as mock_run_with_leadership, \
         caplog.at_level(logging.INFO, logger='flowforge.engine.scheduler'):
        start_scheduler(mock_app)

    mock_run_with_leadership.assert_called_once()
    assert any('leader election' in m.lower() for m in caplog.messages)
