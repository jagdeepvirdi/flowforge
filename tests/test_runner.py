"""Tests for the pipeline runner (engine/runner.py). Uses mock steps — no DB."""
import pytest
from unittest.mock import MagicMock, patch
from flowforge.steps.base import BaseStep, StepResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_step(name, success=True, output_path='', drive_url='', rows=0,
              on_error='stop', error_msg='step failed'):
    """Create a concrete BaseStep subclass with a predictable result."""
    result = StepResult(
        success=success,
        output_path=output_path,
        drive_url=drive_url,
        rows_affected=rows,
        error='' if success else error_msg,
    )

    class MockStep(BaseStep):
        def run(self, context):
            return result

    step = MockStep(name=name, config={'on_error': on_error})
    return step


def run(steps, pipeline_vars=None):
    from flowforge.engine.runner import run_pipeline
    # Patch DB helpers so tests work without a Flask app context
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        return run_pipeline('Test Pipeline', steps, pipeline_vars=pipeline_vars)


# ── Basic execution ───────────────────────────────────────────────────────────

def test_all_steps_run_on_success():
    steps = [make_step('a'), make_step('b'), make_step('c')]
    result = run(steps)
    assert result.success is True
    assert result.steps_run == 3
    assert result.steps_failed == 0


def test_single_step_success():
    result = run([make_step('only')])
    assert result.success is True
    assert 'only' in result.step_results


def test_empty_pipeline_succeeds():
    result = run([])
    assert result.success is True
    assert result.steps_run == 0


# ── on_error = stop ───────────────────────────────────────────────────────────

def test_on_error_stop_halts_pipeline():
    steps = [make_step('a'), make_step('b', success=False, on_error='stop'), make_step('c')]
    result = run(steps)
    assert result.success is False
    assert result.steps_run == 2          # c was never reached
    assert 'c' not in result.step_results
    assert result.error == 'step failed'


def test_on_error_stop_first_step():
    steps = [make_step('a', success=False, on_error='stop'), make_step('b'), make_step('c')]
    result = run(steps)
    assert result.success is False
    assert result.steps_run == 1
    assert result.steps_failed == 1


# ── on_error = continue ───────────────────────────────────────────────────────

def test_on_error_continue_runs_all_steps():
    steps = [make_step('a'), make_step('b', success=False, on_error='continue'), make_step('c')]
    result = run(steps)
    assert result.steps_run == 3
    assert result.steps_failed == 1
    assert 'c' in result.step_results


def test_on_error_continue_pipeline_still_fails():
    """Pipeline result is False if any step failed, even with continue."""
    steps = [make_step('a', success=False, on_error='continue')]
    result = run(steps)
    assert result.steps_failed == 1
    assert result.success is False


def test_multiple_failures_with_continue():
    steps = [
        make_step('a', success=False, on_error='continue'),
        make_step('b', success=False, on_error='continue'),
        make_step('c'),
    ]
    result = run(steps)
    assert result.steps_run == 3
    assert result.steps_failed == 2
    assert result.step_results['c'].success is True


# ── Context threading ─────────────────────────────────────────────────────────

def test_step_output_available_to_next_step():
    """output_path from step A must be in context when step B runs."""
    received_context = {}

    class ProducerStep(BaseStep):
        def run(self, ctx):
            return StepResult(success=True, output_path='/tmp/report.xlsx')

    class ConsumerStep(BaseStep):
        def run(self, ctx):
            received_context.update(ctx)
            return StepResult(success=True)

    steps = [
        ProducerStep('producer', {'on_error': 'stop'}),
        ConsumerStep('consumer', {'on_error': 'stop'}),
    ]
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', steps)

    assert received_context['steps']['producer']['output_path'] == '/tmp/report.xlsx'


def test_drive_url_threaded_to_context():
    class DriveStep(BaseStep):
        def run(self, ctx):
            return StepResult(success=True, drive_url='https://drive.google.com/abc')

    received = {}

    class NextStep(BaseStep):
        def run(self, ctx):
            received.update(ctx)
            return StepResult(success=True)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', [DriveStep('uploader', {'on_error': 'stop'}),
                               NextStep('mailer', {'on_error': 'stop'})])

    assert received['steps']['uploader']['drive_url'] == 'https://drive.google.com/abc'


# ── Pipeline variables ────────────────────────────────────────────────────────

def test_pipeline_vars_in_context():
    received = {}

    class VarStep(BaseStep):
        def run(self, ctx):
            received.update(ctx)
            return StepResult(success=True)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', [VarStep('v', {'on_error': 'stop'})],
                     pipeline_vars={'region': 'APAC', 'period': '2026-05'})

    assert received['region'] == 'APAC'
    assert received['period'] == '2026-05'


# ── Result tracking ───────────────────────────────────────────────────────────

def test_step_results_keyed_by_name():
    result = run([make_step('alpha', output_path='/out.csv'), make_step('beta')])
    assert 'alpha' in result.step_results
    assert result.step_results['alpha'].output_path == '/out.csv'


def test_pipeline_name_in_result():
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        result = run_pipeline('My Report Pipeline', [make_step('x')])
    assert result.pipeline_name == 'My Report Pipeline'


# ── capture_rows context threading ───────────────────────────────────────────

def test_rows_threaded_to_context():
    """rows, table_html, kv_html must land in context['steps'] after a capturing step."""
    received = {}

    class CapturingStep(BaseStep):
        def run(self, ctx):
            return StepResult(
                success=True,
                rows=[{'count': 5, 'status': 'ok'}],
                table_html='<table>...</table>',
                kv_html='<dl>...</dl>',
            )

    class NextStep(BaseStep):
        def run(self, ctx):
            received.update(ctx)
            return StepResult(success=True)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', [
            CapturingStep('query_step', {'on_error': 'stop'}),
            NextStep('email_step', {'on_error': 'stop'}),
        ])

    assert received['steps']['query_step']['rows'] == [{'count': 5, 'status': 'ok'}]
    assert received['steps']['query_step']['table_html'] == '<table>...</table>'
    assert received['steps']['query_step']['kv_html'] == '<dl>...</dl>'


def test_rows_key_present_for_non_capturing_step():
    """rows key must exist in context even when step produces no rows."""
    received = {}

    class NextStep(BaseStep):
        def run(self, ctx):
            received.update(ctx)
            return StepResult(success=True)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test', [
            make_step('plain_step'),
            NextStep('consumer', {'on_error': 'stop'}),
        ])

    assert received['steps']['plain_step']['rows'] == []
    assert received['steps']['plain_step']['table_html'] == ''
    assert received['steps']['plain_step']['kv_html'] == ''


# ── Retry logic ───────────────────────────────────────────────────────────────

def _make_retry_step(name, fail_count=0, on_error='stop', retry_count=0, retry_delay=0):
    """Step that fails the first `fail_count` attempts then succeeds."""
    attempt_box = [0]

    class RetryStep(BaseStep):
        def run(self, ctx):
            attempt_box[0] += 1
            if attempt_box[0] <= fail_count:
                return StepResult(success=False, error='transient error')
            return StepResult(success=True)

    cfg = {'on_error': on_error, 'retry_count': retry_count, 'retry_delay_seconds': retry_delay}
    step = RetryStep(name=name, config=cfg)
    return step


def _run_with_patches(steps, **kwargs):
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('time.sleep'):
        return run_pipeline('Retry Test', steps, **kwargs)


def test_retry_zero_retries_fails_immediately():
    """With retry_count=0, a failing step fails without retrying."""
    step = _make_retry_step('s', fail_count=1, retry_count=0, retry_delay=0)
    result = _run_with_patches([step])
    assert result.success is False
    assert result.steps_failed == 1


def test_retry_succeeds_on_second_attempt():
    """Step that fails once and then succeeds with retry_count=1."""
    step = _make_retry_step('s', fail_count=1, retry_count=1, retry_delay=0)
    result = _run_with_patches([step])
    assert result.success is True
    assert result.steps_failed == 0


def test_retry_exhausted_still_fails():
    """Step that always fails uses all retries then marks failure."""
    step = _make_retry_step('s', fail_count=5, retry_count=2, retry_delay=0)
    result = _run_with_patches([step])
    assert result.success is False


def test_retry_calls_sleep_with_delay():
    """time.sleep is called with the configured retry_delay_seconds."""
    step = _make_retry_step('s', fail_count=1, retry_count=1, retry_delay=5)
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('time.sleep') as mock_sleep:
        run_pipeline('Retry Test', [step])
    mock_sleep.assert_called_with(5)


def test_retry_count_capped_at_10():
    """retry_count > 10 is silently capped to 10."""
    attempt_box = [0]

    class CountingStep(BaseStep):
        def run(self, ctx):
            attempt_box[0] += 1
            return StepResult(success=False, error='always fails')

    cfg = {'on_error': 'stop', 'retry_count': 999, 'retry_delay_seconds': 0}
    step = CountingStep('s', config=cfg)
    _run_with_patches([step])
    # 1 initial + 10 retries = 11 calls max
    assert attempt_box[0] <= 11


def test_retry_delay_capped_at_3600():
    """retry_delay_seconds > 3600 is capped to 3600."""
    step = _make_retry_step('s', fail_count=1, retry_count=1, retry_delay=9999)
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('time.sleep') as mock_sleep:
        run_pipeline('Retry Test', [step])
    mock_sleep.assert_called_with(3600)


def test_retry_negative_count_treated_as_zero():
    """Negative retry_count is clamped to 0."""
    step = _make_retry_step('s', fail_count=1, retry_count=-5, retry_delay=0)
    result = _run_with_patches([step])
    assert result.success is False
    assert result.steps_failed == 1


# ── Failure webhook ───────────────────────────────────────────────────────────

def test_fire_failure_webhook_posts_json():
    from flowforge.engine.runner import _fire_failure_webhook
    payload = {'pipeline_name': 'Test', 'error_message': 'boom'}
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        _fire_failure_webhook('http://example.com/hook', payload)
    mock_open.assert_called_once()
    req = mock_open.call_args[0][0]
    import json
    body = json.loads(req.data)
    assert body['pipeline_name'] == 'Test'
    assert body['error_message'] == 'boom'


def test_fire_failure_webhook_content_type_header():
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        _fire_failure_webhook('http://example.com/hook', {})
    req = mock_open.call_args[0][0]
    assert req.get_header('Content-type') == 'application/json'


def test_fire_failure_webhook_empty_url_does_nothing():
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen') as mock_open:
        _fire_failure_webhook('', {'pipeline_name': 'Test'})
    mock_open.assert_not_called()


def test_fire_failure_webhook_none_url_does_nothing():
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen') as mock_open:
        _fire_failure_webhook(None, {})
    mock_open.assert_not_called()


def test_fire_failure_webhook_error_does_not_propagate():
    """Network errors in the webhook must not raise."""
    from flowforge.engine.runner import _fire_failure_webhook
    with patch('urllib.request.urlopen', side_effect=Exception('network error')):
        _fire_failure_webhook('http://example.com/hook', {})  # must not raise


def test_webhook_called_when_pipeline_fails():
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('flowforge.engine.runner._fire_failure_webhook') as mock_webhook:
        run_pipeline(
            'Test Pipeline',
            [make_step('fail', success=False)],
            on_failure_webhook_url='http://example.com/hook',
        )
    mock_webhook.assert_called_once()
    url = mock_webhook.call_args[0][0]
    assert url == 'http://example.com/hook'


def test_webhook_not_called_when_pipeline_succeeds():
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('flowforge.engine.runner._fire_failure_webhook') as mock_webhook:
        run_pipeline(
            'Test Pipeline',
            [make_step('ok', success=True)],
            on_failure_webhook_url='http://example.com/hook',
        )
    mock_webhook.assert_not_called()


def test_webhook_not_called_when_url_not_set():
    from flowforge.engine.runner import run_pipeline
    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('flowforge.engine.runner._fire_failure_webhook') as mock_webhook:
        run_pipeline('Test Pipeline', [make_step('fail', success=False)])
    mock_webhook.assert_not_called()


def test_webhook_payload_contains_expected_keys():
    from flowforge.engine.runner import run_pipeline
    captured = {}

    def capture_webhook(url, payload):
        captured.update(payload)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('flowforge.engine.runner._fire_failure_webhook', side_effect=capture_webhook):
        run_pipeline(
            'My Pipeline',
            [make_step('bad_step', success=False, error_msg='DB timeout')],
            on_failure_webhook_url='http://example.com/hook',
        )

    assert 'pipeline_name' in captured
    assert 'error_step' in captured
    assert 'error_message' in captured
    assert captured['pipeline_name'] == 'My Pipeline'
