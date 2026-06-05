"""Extended tests for engine/runner.py — parallel waves, DB helpers, _expose_step_outputs."""
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch, call

import pytest

from flowforge.steps.base import BaseStep, StepResult


# ── helpers ───────────────────────────────────────────────────────────────────

def make_step(name, success=True, on_error='stop', parallel_group=None,
              output_variables=None, error_msg='step failed'):
    result = StepResult(
        success=success,
        error='' if success else error_msg,
        output_variables=output_variables or {},
    )

    class MockStep(BaseStep):
        def run(self, ctx):
            return result

    cfg = {'on_error': on_error}
    if parallel_group:
        cfg['parallel_group'] = parallel_group
    return MockStep(name=name, config=cfg)


def run_with_patches(steps, **kwargs):
    """Run pipeline with all DB helpers mocked."""
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        return run_pipeline('Test Pipeline', steps, **kwargs)


# ── _build_execution_waves ────────────────────────────────────────────────────

def test_build_waves_sequential_steps():
    """Each step without parallel_group → separate single-step waves."""
    from flowforge.engine.runner import _build_execution_waves
    steps = [make_step('a'), make_step('b'), make_step('c')]
    waves = _build_execution_waves(steps)
    assert len(waves) == 3
    assert all(len(w) == 1 for w in waves)


def test_build_waves_empty_steps():
    from flowforge.engine.runner import _build_execution_waves
    waves = _build_execution_waves([])
    assert waves == []


def test_build_waves_same_parallel_group_grouped():
    """Steps with the same parallel_group → one wave."""
    from flowforge.engine.runner import _build_execution_waves
    steps = [
        make_step('a', parallel_group='g1'),
        make_step('b', parallel_group='g1'),
        make_step('c', parallel_group='g1'),
    ]
    waves = _build_execution_waves(steps)
    assert len(waves) == 1
    assert len(waves[0]) == 3


def test_build_waves_mixed_parallel_and_sequential():
    from flowforge.engine.runner import _build_execution_waves
    steps = [
        make_step('seq1'),
        make_step('p1', parallel_group='g1'),
        make_step('p2', parallel_group='g1'),
        make_step('seq2'),
    ]
    waves = _build_execution_waves(steps)
    # seq1 → [p1, p2] → seq2
    assert len(waves) == 3
    assert len(waves[0]) == 1  # seq1
    assert len(waves[1]) == 2  # p1, p2
    assert len(waves[2]) == 1  # seq2


def test_build_waves_different_parallel_groups():
    """Different parallel_group values → separate waves."""
    from flowforge.engine.runner import _build_execution_waves
    steps = [
        make_step('a', parallel_group='g1'),
        make_step('b', parallel_group='g2'),
    ]
    waves = _build_execution_waves(steps)
    assert len(waves) == 2
    assert waves[0][0].name == 'a'
    assert waves[1][0].name == 'b'


def test_build_waves_parallel_group_none_breaks_group():
    """A step without parallel_group between two groups breaks grouping."""
    from flowforge.engine.runner import _build_execution_waves
    steps = [
        make_step('a', parallel_group='g1'),
        make_step('b'),  # no group
        make_step('c', parallel_group='g1'),
    ]
    waves = _build_execution_waves(steps)
    # g1 group interrupted by sequential step
    assert len(waves) == 3


# ── _expose_step_outputs ──────────────────────────────────────────────────────

def test_expose_step_outputs_sets_context_fields():
    from flowforge.engine.runner import _expose_step_outputs
    context = {'steps': {}}
    result = StepResult(
        success=True,
        output_path='/tmp/report.xlsx',
        drive_url='https://drive.google.com/xyz',
        rows_affected=42,
    )
    _expose_step_outputs(context, 'MyPipeline', 'gen_report', result)
    step_ctx = context['steps']['gen_report']
    assert step_ctx['output_path'] == '/tmp/report.xlsx'
    assert step_ctx['drive_url'] == 'https://drive.google.com/xyz'
    assert step_ctx['rows_affected'] == 42


def test_expose_step_outputs_non_reserved_vars_merged():
    from flowforge.engine.runner import _expose_step_outputs
    context = {'steps': {}}
    result = StepResult(
        success=True,
        output_variables={'my_custom_var': 'hello', 'another': 42},
    )
    _expose_step_outputs(context, 'P', 's', result)
    assert context['my_custom_var'] == 'hello'
    assert context['another'] == 42


def test_expose_step_outputs_reserved_key_not_overwritten(caplog):
    """output_variables with a reserved key (e.g. 'run_id') must not be merged into context."""
    import logging
    from flowforge.engine.runner import _expose_step_outputs
    context = {'steps': {}, 'run_id': 'original-run-id'}
    result = StepResult(
        success=True,
        output_variables={'run_id': 'hijacked'},
    )
    with caplog.at_level(logging.WARNING):
        _expose_step_outputs(context, 'P', 'bad_step', result)
    assert context['run_id'] == 'original-run-id'
    assert any('reserved' in r.message.lower() for r in caplog.records)


def test_expose_step_outputs_env_key_not_overwritten():
    """'env' is a reserved meta key and must not be overwritten."""
    from flowforge.engine.runner import _expose_step_outputs
    context = {'steps': {}, 'env': {'SECRET': 'value'}}
    result = StepResult(
        success=True,
        output_variables={'env': {'injected': True}},
    )
    _expose_step_outputs(context, 'P', 'step', result)
    assert context['env'] == {'SECRET': 'value'}


def test_expose_step_outputs_no_output_variables():
    """Steps with no output_variables only populate steps[name] dict."""
    from flowforge.engine.runner import _expose_step_outputs
    context = {'steps': {}}
    result = StepResult(success=True)
    _expose_step_outputs(context, 'P', 'step', result)
    assert 'step' in context['steps']
    # No extra keys injected at top level
    assert 'some_var' not in context


# ── parallel waves in run_pipeline ───────────────────────────────────────────

def test_parallel_all_steps_succeed():
    """All parallel steps succeed → pipeline success."""
    steps = [
        make_step('p1', parallel_group='g1'),
        make_step('p2', parallel_group='g1'),
    ]
    result = run_with_patches(steps)
    assert result.success is True
    assert result.steps_run == 2
    assert 'p1' in result.step_results
    assert 'p2' in result.step_results


def test_parallel_one_fails_on_error_stop():
    """One parallel step fails with on_error=stop → pipeline fails."""
    steps = [
        make_step('p1', success=False, on_error='stop', parallel_group='g1'),
        make_step('p2', parallel_group='g1'),
    ]
    result = run_with_patches(steps)
    assert result.success is False
    assert result.steps_failed >= 1


def test_parallel_one_fails_on_error_continue():
    """One parallel step fails with on_error=continue → pipeline still fails but continues."""
    steps = [
        make_step('p1', success=False, on_error='continue', parallel_group='g1'),
        make_step('p2', parallel_group='g1'),
        make_step('seq_after'),
    ]
    result = run_with_patches(steps)
    assert result.success is False
    assert result.steps_failed == 1
    # seq_after should still have run (on_error=continue on parallel step)
    assert 'seq_after' in result.step_results


def test_parallel_wave_followed_by_sequential():
    """Parallel wave followed by sequential step — all run on success."""
    steps = [
        make_step('p1', parallel_group='g1'),
        make_step('p2', parallel_group='g1'),
        make_step('seq'),
    ]
    result = run_with_patches(steps)
    assert result.success is True
    assert result.steps_run == 3


def test_parallel_mixed_with_sequential_all_succeed():
    steps = [
        make_step('a'),
        make_step('p1', parallel_group='g1'),
        make_step('p2', parallel_group='g1'),
        make_step('b'),
    ]
    result = run_with_patches(steps)
    assert result.success is True
    assert result.steps_run == 4


# ── _write_step_run ───────────────────────────────────────────────────────────

def test_write_step_run_noop_when_run_record_none():
    """_write_step_run returns immediately if run_record is None — no DB import."""
    from flowforge.engine.runner import _write_step_run
    step = make_step('s')
    result = StepResult(success=True)
    t = datetime.now(UTC)
    # Should not raise even without app context
    _write_step_run(None, step, 1, result, t, t, 100)


def test_write_step_run_creates_step_run_record(app):
    """_write_step_run creates a StepRun DB record when run_record is set."""
    from flowforge.engine.runner import _write_step_run
    from flowforge.db.models import PipelineRun, StepRun, db

    with app.app_context():
        # Create a parent PipelineRun
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_name='__writer_test__',
            status='running',
            started_at=datetime.now(UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

        step = make_step('test_step')
        step.step_type = 'db_query'
        result = StepResult(success=True, rows_affected=5, logs='some log')
        t0 = datetime.now(UTC)
        t1 = datetime.now(UTC)

        _write_step_run(run, step, 1, result, t0, t1, 50)

        sr = db.session.query(StepRun).filter_by(
            pipeline_run_id=run_id, step_name='test_step'
        ).first()
        assert sr is not None
        assert sr.status == 'success'
        assert sr.rows_affected == 5

        # cleanup
        db.session.delete(sr)
        db.session.delete(run)
        db.session.commit()


def test_write_step_run_swallows_sqlalchemy_error(app):
    """SQLAlchemyError during _write_step_run must not propagate."""
    from sqlalchemy.exc import SQLAlchemyError
    from flowforge.engine.runner import _write_step_run

    mock_run = MagicMock()
    mock_run.id = str(uuid.uuid4())

    step = make_step('s')
    result = StepResult(success=True)
    t = datetime.now(UTC)

    with patch('flowforge.engine.runner._write_step_run') as patched:
        # We test the real function by calling it with a mock that triggers the error
        pass

    # Call the real function with DB mocked to raise
    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.add.side_effect = SQLAlchemyError('db error')
        # Must not raise
        with app.app_context():
            try:
                _write_step_run(mock_run, step, 1, result, t, t, 10)
            except Exception:
                pytest.fail("_write_step_run raised an exception, expected it to be swallowed")


# ── _finish_run_record ────────────────────────────────────────────────────────

def test_finish_run_record_noop_when_none():
    """_finish_run_record is a no-op when run_record is None."""
    from flowforge.engine.runner import _finish_run_record
    _finish_run_record(None, success=True)  # should not raise


def test_finish_run_record_sets_success(app):
    from flowforge.engine.runner import _finish_run_record
    from flowforge.db.models import PipelineRun, db

    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_name='__finish_test__',
            status='running',
            started_at=datetime.now(UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()

        _finish_run_record(run, success=True)

        assert run.status == 'success'
        assert run.finished_at is not None

        db.session.delete(run)
        db.session.commit()


def test_finish_run_record_sets_failure_with_details(app):
    from flowforge.engine.runner import _finish_run_record
    from flowforge.db.models import PipelineRun, db

    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_name='__finish_fail_test__',
            status='running',
            started_at=datetime.now(UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()

        _finish_run_record(run, success=False, error_step='bad_step', error_message='DB timeout')

        assert run.status == 'failed'
        assert run.error_step == 'bad_step'
        assert run.error_message == 'DB timeout'

        db.session.delete(run)
        db.session.commit()


def test_finish_run_record_swallows_sqlalchemy_error():
    """SQLAlchemyError during _finish_run_record must not propagate."""
    from sqlalchemy.exc import SQLAlchemyError
    from flowforge.engine.runner import _finish_run_record

    mock_run = MagicMock()
    mock_run.started_at = datetime.now(UTC)

    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.commit.side_effect = SQLAlchemyError('commit failed')
        try:
            _finish_run_record(mock_run, success=True)
        except Exception:
            pytest.fail("_finish_run_record raised, expected swallow")


# ── _create_run_record ────────────────────────────────────────────────────────

def test_create_run_record_returns_none_on_sqla_error():
    """If SQLAlchemy raises, _create_run_record returns None."""
    from sqlalchemy.exc import SQLAlchemyError
    from flowforge.engine.runner import _create_run_record

    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.add.side_effect = SQLAlchemyError('no connection')
        result = _create_run_record(None, 'MyPipe', 'api')
        assert result is None


def test_create_run_record_with_existing_run_id(app):
    """existing_run_id → fetches via db.session.get."""
    from flowforge.engine.runner import _create_run_record
    from flowforge.db.models import PipelineRun, db

    with app.app_context():
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_name='__create_existing__',
            status='running',
            started_at=datetime.now(UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

        fetched = _create_run_record(None, 'MyPipe', 'api', existing_run_id=run_id)
        assert fetched is not None
        assert fetched.id == run_id

        db.session.delete(run)
        db.session.commit()


def test_create_run_record_creates_new(app):
    """No existing_run_id → creates a new PipelineRun."""
    from flowforge.engine.runner import _create_run_record
    from flowforge.db.models import PipelineRun, db

    with app.app_context():
        run = _create_run_record(None, '__created_pipe__', 'api')
        assert run is not None
        assert run.status == 'running'
        assert run.pipeline_name == '__created_pipe__'

        db.session.delete(run)
        db.session.commit()


# ── _get_last_success_ts ──────────────────────────────────────────────────────

def test_get_last_success_ts_returns_empty_when_no_run():
    """No successful run → returns empty string."""
    from flowforge.engine.runner import _get_last_success_ts

    fake_pipeline_id = str(uuid.uuid4())
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        with patch('flowforge.db.models.db') as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None
            result = _get_last_success_ts(fake_pipeline_id, '%Y-%m-%d')
    assert result == ''


def test_get_last_success_ts_returns_formatted_date(app):
    from flowforge.engine.runner import _get_last_success_ts
    from flowforge.db.models import Pipeline, PipelineRun, db

    pid = str(uuid.uuid4())
    with app.app_context():
        pipeline = Pipeline(id=pid, name='__ts_test_pipeline__', enabled=True)
        db.session.add(pipeline)
        db.session.flush()
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pid,
            pipeline_name='__ts_test__',
            status='success',
            started_at=datetime(2026, 5, 1, tzinfo=UTC),
            finished_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC),
            triggered_by='test',
        )
        db.session.add(run)
        db.session.commit()

        result = _get_last_success_ts(pid, '%Y-%m-%d')
        assert result == '2026-05-01'

        db.session.delete(run)
        db.session.delete(pipeline)
        db.session.commit()


def test_get_last_success_ts_returns_empty_on_exception():
    """Exception during query → returns empty string, does not raise."""
    from flowforge.engine.runner import _get_last_success_ts
    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.query.side_effect = RuntimeError('no DB')
        result = _get_last_success_ts('fake-id', '%Y-%m-%d')
    assert result == ''


# ── _fire_failure_webhook ─────────────────────────────────────────────────────

def test_fire_failure_webhook_empty_url_noop():
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen') as mock_open:
        _fire_failure_webhook('', {'key': 'val'})
    mock_open.assert_not_called()


def test_fire_failure_webhook_none_url_noop():
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen') as mock_open:
        _fire_failure_webhook(None, {})
    mock_open.assert_not_called()


def test_fire_failure_webhook_posts_to_url():
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        _fire_failure_webhook('http://example.com/hook', {'pipeline_name': 'Test'})
    mock_open.assert_called_once()


def test_fire_failure_webhook_swallows_exception():
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen', side_effect=Exception('network error')):
        # Must not raise
        _fire_failure_webhook('http://example.com/hook', {})


# ── _trigger_downstream_pipelines ────────────────────────────────────────────

def test_trigger_downstream_pipelines_no_fanout_returns_early():
    """No dependencies → returns without error."""
    from flowforge.engine.runner import _trigger_downstream_pipelines

    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = []
        # Should not raise
        _trigger_downstream_pipelines(str(uuid.uuid4()))


def test_trigger_downstream_pipelines_swallows_exception():
    """Exceptions in dependency trigger must not propagate."""
    from flowforge.engine.runner import _trigger_downstream_pipelines

    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.query.side_effect = RuntimeError('no app ctx')
        # Must not raise
        _trigger_downstream_pipelines(str(uuid.uuid4()))
