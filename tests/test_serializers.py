"""Unit tests for API serializers (serializers.py).

Pure unit tests — no DB, no Flask app context required.
MagicMock is used to create fake ORM objects.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from flowforge.api.serializers import run_dict, step_run_dict


# ── Helpers ───────────────────────────────────────────────────────────────────

_TS = datetime(2026, 5, 25, 9, 0, 0, tzinfo=timezone.utc)
_TS2 = datetime(2026, 5, 25, 9, 1, 30, tzinfo=timezone.utc)


def _make_run(**kwargs):
    r = MagicMock()
    r.id = kwargs.get('id', 'run-uuid-1')
    r.pipeline_id = kwargs.get('pipeline_id', 'pipe-uuid-1')
    r.pipeline_name = kwargs.get('pipeline_name', 'Monthly Report')
    r.status = kwargs.get('status', 'success')
    r.started_at = kwargs.get('started_at', _TS)
    r.finished_at = kwargs.get('finished_at', _TS2)
    r.duration_ms = kwargs.get('duration_ms', 90000)
    r.triggered_by = kwargs.get('triggered_by', 'scheduler')
    r.error_step = kwargs.get('error_step', None)
    r.error_message = kwargs.get('error_message', None)
    r.step_runs = kwargs.get('step_runs', [])
    return r


def _make_step_run(**kwargs):
    s = MagicMock()
    s.id = kwargs.get('id', 'sr-uuid-1')
    s.step_name = kwargs.get('step_name', 'Generate Report')
    s.step_type = kwargs.get('step_type', 'report')
    s.step_order = kwargs.get('step_order', 1)
    s.status = kwargs.get('status', 'success')
    s.started_at = kwargs.get('started_at', _TS)
    s.finished_at = kwargs.get('finished_at', _TS2)
    s.duration_ms = kwargs.get('duration_ms', 45000)
    s.rows_affected = kwargs.get('rows_affected', 500)
    s.output_path = kwargs.get('output_path', '/reports/out.xlsx')
    s.drive_url = kwargs.get('drive_url', None)
    s.email_sent_to = kwargs.get('email_sent_to', None)
    s.logs = kwargs.get('logs', None)
    s.error_message = kwargs.get('error_message', None)
    return s


# ── run_dict ──────────────────────────────────────────────────────────────────

def test_run_dict_contains_all_fields():
    d = run_dict(_make_run())
    for key in ('id', 'pipeline_id', 'pipeline_name', 'status',
                'started_at', 'finished_at', 'duration_ms',
                'triggered_by', 'error_step', 'error_message'):
        assert key in d, f"Missing key: {key}"


def test_run_dict_id_value():
    d = run_dict(_make_run(id='my-run-id'))
    assert d['id'] == 'my-run-id'


def test_run_dict_pipeline_name():
    d = run_dict(_make_run(pipeline_name='Finance Pipeline'))
    assert d['pipeline_name'] == 'Finance Pipeline'


def test_run_dict_status():
    d = run_dict(_make_run(status='failed'))
    assert d['status'] == 'failed'


def test_run_dict_started_at_is_iso_string():
    d = run_dict(_make_run(started_at=_TS))
    assert d['started_at'] == _TS.isoformat()


def test_run_dict_finished_at_is_iso_string():
    d = run_dict(_make_run(finished_at=_TS2))
    assert d['finished_at'] == _TS2.isoformat()


def test_run_dict_started_at_none():
    d = run_dict(_make_run(started_at=None))
    assert d['started_at'] is None


def test_run_dict_finished_at_none():
    d = run_dict(_make_run(finished_at=None))
    assert d['finished_at'] is None


def test_run_dict_both_timestamps_none():
    d = run_dict(_make_run(started_at=None, finished_at=None))
    assert d['started_at'] is None
    assert d['finished_at'] is None


def test_run_dict_duration_ms():
    d = run_dict(_make_run(duration_ms=12345))
    assert d['duration_ms'] == 12345


def test_run_dict_triggered_by():
    d = run_dict(_make_run(triggered_by='web_ui'))
    assert d['triggered_by'] == 'web_ui'


def test_run_dict_error_fields_none_on_success():
    d = run_dict(_make_run(error_step=None, error_message=None))
    assert d['error_step'] is None
    assert d['error_message'] is None


def test_run_dict_error_fields_set_on_failure():
    d = run_dict(_make_run(
        status='failed',
        error_step='Generate Report',
        error_message='Connection refused',
    ))
    assert d['error_step'] == 'Generate Report'
    assert d['error_message'] == 'Connection refused'


def test_run_dict_no_step_runs_by_default():
    d = run_dict(_make_run())
    assert 'step_runs' not in d


def test_run_dict_include_steps_false():
    d = run_dict(_make_run(), include_steps=False)
    assert 'step_runs' not in d


def test_run_dict_include_steps_empty():
    d = run_dict(_make_run(step_runs=[]), include_steps=True)
    assert d['step_runs'] == []


def test_run_dict_include_steps_returns_list():
    sr = _make_step_run()
    d = run_dict(_make_run(step_runs=[sr]), include_steps=True)
    assert isinstance(d['step_runs'], list)
    assert len(d['step_runs']) == 1


def test_run_dict_include_steps_sorted_by_order():
    sr1 = _make_step_run(id='s1', step_name='Step1', step_order=2)
    sr2 = _make_step_run(id='s2', step_name='Step2', step_order=1)
    d = run_dict(_make_run(step_runs=[sr1, sr2]), include_steps=True)
    assert d['step_runs'][0]['step_order'] == 1
    assert d['step_runs'][1]['step_order'] == 2


def test_run_dict_include_steps_three_in_order():
    steps = [
        _make_step_run(step_name='C', step_order=3),
        _make_step_run(step_name='A', step_order=1),
        _make_step_run(step_name='B', step_order=2),
    ]
    d = run_dict(_make_run(step_runs=steps), include_steps=True)
    names = [s['step_name'] for s in d['step_runs']]
    assert names == ['A', 'B', 'C']


# ── step_run_dict ─────────────────────────────────────────────────────────────

def test_step_run_dict_contains_all_fields():
    d = step_run_dict(_make_step_run())
    for key in ('id', 'step_name', 'step_type', 'step_order', 'status',
                'started_at', 'finished_at', 'duration_ms', 'rows_affected',
                'output_path', 'drive_url', 'email_sent_to', 'logs', 'error_message'):
        assert key in d, f"Missing key: {key}"


def test_step_run_dict_id():
    d = step_run_dict(_make_step_run(id='sr-42'))
    assert d['id'] == 'sr-42'


def test_step_run_dict_step_name():
    d = step_run_dict(_make_step_run(step_name='Send Email'))
    assert d['step_name'] == 'Send Email'


def test_step_run_dict_step_type():
    d = step_run_dict(_make_step_run(step_type='email'))
    assert d['step_type'] == 'email'


def test_step_run_dict_step_order():
    d = step_run_dict(_make_step_run(step_order=3))
    assert d['step_order'] == 3


def test_step_run_dict_status():
    d = step_run_dict(_make_step_run(status='failed'))
    assert d['status'] == 'failed'


def test_step_run_dict_started_at_is_iso():
    d = step_run_dict(_make_step_run(started_at=_TS))
    assert d['started_at'] == _TS.isoformat()


def test_step_run_dict_finished_at_is_iso():
    d = step_run_dict(_make_step_run(finished_at=_TS2))
    assert d['finished_at'] == _TS2.isoformat()


def test_step_run_dict_started_at_none():
    d = step_run_dict(_make_step_run(started_at=None))
    assert d['started_at'] is None


def test_step_run_dict_finished_at_none():
    d = step_run_dict(_make_step_run(finished_at=None))
    assert d['finished_at'] is None


def test_step_run_dict_rows_affected():
    d = step_run_dict(_make_step_run(rows_affected=1234))
    assert d['rows_affected'] == 1234


def test_step_run_dict_output_path():
    d = step_run_dict(_make_step_run(output_path='/tmp/report.xlsx'))
    assert d['output_path'] == '/tmp/report.xlsx'


def test_step_run_dict_drive_url():
    d = step_run_dict(_make_step_run(drive_url='https://drive.google.com/file/xyz'))
    assert d['drive_url'] == 'https://drive.google.com/file/xyz'


def test_step_run_dict_email_sent_to_none_returns_empty_list():
    d = step_run_dict(_make_step_run(email_sent_to=None))
    assert d['email_sent_to'] == []


def test_step_run_dict_email_sent_to_list():
    d = step_run_dict(_make_step_run(email_sent_to=['a@b.com', 'c@d.com']))
    assert d['email_sent_to'] == ['a@b.com', 'c@d.com']


def test_step_run_dict_email_sent_to_empty_list():
    d = step_run_dict(_make_step_run(email_sent_to=[]))
    assert d['email_sent_to'] == []


def test_step_run_dict_logs():
    d = step_run_dict(_make_step_run(logs='Step completed\nRows: 500'))
    assert d['logs'] == 'Step completed\nRows: 500'


def test_step_run_dict_error_message():
    d = step_run_dict(_make_step_run(error_message='Timeout'))
    assert d['error_message'] == 'Timeout'


def test_step_run_dict_error_message_none():
    d = step_run_dict(_make_step_run(error_message=None))
    assert d['error_message'] is None
