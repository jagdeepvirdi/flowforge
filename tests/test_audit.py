"""Unit tests for audit log functions (NEW-3).

All tests use a temp log directory and an isolated logger so they don't
touch the real audit.log and don't interfere with each other.
"""
import io
import json
import logging
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(autouse=True)
def isolated_audit_logger(tmp_path, monkeypatch):
    """Reset the module-level _logger and _LOG_DIR before each test."""
    import flowforge.audit as audit_mod

    # Clear any handlers already attached to the logger
    logger = logging.getLogger('flowforge.audit')
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)

    # Patch both the cached logger instance AND the directory (computed at import)
    monkeypatch.setattr(audit_mod, '_logger', None)
    monkeypatch.setattr(audit_mod, '_LOG_DIR', tmp_path)

    yield tmp_path

    # Cleanup handlers after test
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)
    audit_mod._logger = None


def _read_log(tmp_path: Path) -> str:
    log_file = tmp_path / 'audit.log'
    return log_file.read_text() if log_file.exists() else ''


# ── log_login / log_logout ────────────────────────────────────────────────────

def test_log_login_success_written(isolated_audit_logger):
    from flowforge import audit
    audit.log_login('alice', success=True, remote_addr='1.2.3.4')
    content = _read_log(isolated_audit_logger)
    assert 'LOGIN' in content
    assert 'SUCCESS' in content
    assert 'alice' in content
    assert '1.2.3.4' in content


def test_log_login_failure_written(isolated_audit_logger):
    from flowforge import audit
    audit.log_login('baduser', success=False, remote_addr='10.0.0.1')
    content = _read_log(isolated_audit_logger)
    assert 'FAILED' in content
    assert 'baduser' in content


def test_log_logout_written(isolated_audit_logger):
    from flowforge import audit
    audit.log_logout('alice', remote_addr='1.2.3.4')
    content = _read_log(isolated_audit_logger)
    assert 'LOGOUT' in content
    assert 'alice' in content


# ── log_connection_change (NEW-3) ─────────────────────────────────────────────

def test_log_connection_change_created(isolated_audit_logger):
    from flowforge import audit
    audit.log_connection_change('CREATED', 'Production DB', 'some-uuid-1')
    content = _read_log(isolated_audit_logger)
    assert 'CONNECTION' in content
    assert 'CREATED' in content
    assert 'Production DB' in content
    assert 'some-uuid-1' in content


def test_log_connection_change_updated(isolated_audit_logger):
    from flowforge import audit
    audit.log_connection_change('UPDATED', 'Staging DB', 'some-uuid-2')
    content = _read_log(isolated_audit_logger)
    assert 'UPDATED' in content
    assert 'Staging DB' in content


def test_log_connection_change_deleted(isolated_audit_logger):
    from flowforge import audit
    audit.log_connection_change('DELETED', 'Old DB', 'some-uuid-3')
    content = _read_log(isolated_audit_logger)
    assert 'DELETED' in content
    assert 'Old DB' in content


# ── log_provider_change (NEW-3) ───────────────────────────────────────────────

def test_log_provider_change_created(isolated_audit_logger):
    from flowforge import audit
    audit.log_provider_change('CREATED', 'Company Gmail', 'prov-uuid-1')
    content = _read_log(isolated_audit_logger)
    assert 'PROVIDER' in content
    assert 'CREATED' in content
    assert 'Company Gmail' in content
    assert 'prov-uuid-1' in content


def test_log_provider_change_deleted(isolated_audit_logger):
    from flowforge import audit
    audit.log_provider_change('DELETED', 'Old SMTP', 'prov-uuid-2')
    content = _read_log(isolated_audit_logger)
    assert 'DELETED' in content
    assert 'Old SMTP' in content


# ── log_email_sent (NEW-3) ────────────────────────────────────────────────────

def test_log_email_sent_written(isolated_audit_logger):
    from flowforge import audit
    audit.log_email_sent(
        pipeline_name='Monthly Revenue',
        step_name='Send Report',
        subject='Revenue Report May 2026',
        recipients=['a@example.com', 'b@example.com'],
        attachment_names=['report.xlsx'],
    )
    content = _read_log(isolated_audit_logger)
    assert 'EMAIL_SENT' in content
    assert 'Monthly Revenue' in content
    assert 'Revenue Report May 2026' in content
    assert 'recipients=2' in content
    assert 'report.xlsx' in content


def test_log_email_sent_no_attachments(isolated_audit_logger):
    from flowforge import audit
    audit.log_email_sent(
        pipeline_name='Weekly Summary',
        step_name='Notify Team',
        subject='Summary',
        recipients=['a@example.com'],
        attachment_names=[],
    )
    content = _read_log(isolated_audit_logger)
    assert 'EMAIL_SENT' in content
    assert 'none' in content


def test_log_email_sent_recipient_count(isolated_audit_logger):
    from flowforge import audit
    audit.log_email_sent('P', 'S', 'Subj', ['x@x.com', 'y@y.com', 'z@z.com'], [])
    content = _read_log(isolated_audit_logger)
    assert 'recipients=3' in content


# ── log_report_exported (NEW-3) ───────────────────────────────────────────────

def test_log_report_exported_written(isolated_audit_logger):
    from flowforge import audit
    audit.log_report_exported(
        pipeline_name='Finance Pipeline',
        step_name='Generate Excel',
        output_filename='revenue_2026_05.xlsx',
        row_count=1500,
        fmt='excel',
    )
    content = _read_log(isolated_audit_logger)
    assert 'REPORT_EXPORTED' in content
    assert 'Finance Pipeline' in content
    assert 'revenue_2026_05.xlsx' in content
    assert 'rows=1500' in content
    assert 'excel' in content


def test_log_report_exported_csv_format(isolated_audit_logger):
    from flowforge import audit
    audit.log_report_exported('P', 'S', 'data.csv', row_count=0, fmt='csv')
    content = _read_log(isolated_audit_logger)
    assert 'REPORT_EXPORTED' in content
    assert 'csv' in content


# ── Audit called from routes — verified via mock (NEW-3 integration) ──────────

def test_audit_called_on_connection_create(client, headers):
    """Creating a DB connection must call log_connection_change('CREATED', ...)."""
    import flowforge.audit as audit_mod
    with patch.object(audit_mod, 'log_connection_change') as mock_log:
        payload = {
            'name': '__audit_conn_create__',
            'db_type': 'postgresql',
            'config': {'host': 'localhost', 'port': 5432, 'database': 'test',
                       'username': 'u', 'password': 'p'},
        }
        resp = client.post('/api/db-connections', json=payload, headers=headers)
        assert resp.status_code == 201
        conn_id = resp.get_json()['id']

    mock_log.assert_called_once()
    args = mock_log.call_args[0]
    assert args[0] == 'CREATED'
    assert '__audit_conn_create__' in args[1]

    client.delete(f'/api/db-connections/{conn_id}', headers=headers)


def test_audit_called_on_connection_delete(client, headers):
    """Deleting a DB connection must call log_connection_change('DELETED', ...)."""
    payload = {
        'name': '__audit_conn_delete__',
        'db_type': 'postgresql',
        'config': {'host': 'localhost', 'port': 5432, 'database': 'test',
                   'username': 'u', 'password': 'p'},
    }
    resp = client.post('/api/db-connections', json=payload, headers=headers)
    conn_id = resp.get_json()['id']

    import flowforge.audit as audit_mod
    with patch.object(audit_mod, 'log_connection_change') as mock_log:
        del_resp = client.delete(f'/api/db-connections/{conn_id}', headers=headers)
        assert del_resp.status_code == 200

    mock_log.assert_called_once()
    assert mock_log.call_args[0][0] == 'DELETED'


def test_audit_called_on_provider_create(client, headers):
    """Creating an email provider must call log_provider_change('CREATED', ...)."""
    import flowforge.audit as audit_mod
    with patch.object(audit_mod, 'log_provider_change') as mock_log:
        payload = {
            'name': '__audit_provider_create__',
            'provider_type': 'smtp',
            'config': {'host': 'smtp.example.com', 'port': 587,
                       'username': 'u', 'password': 'p'},
        }
        resp = client.post('/api/email-providers', json=payload, headers=headers)
        assert resp.status_code == 201
        pid = resp.get_json()['id']

    mock_log.assert_called_once()
    args = mock_log.call_args[0]
    assert args[0] == 'CREATED'
    assert '__audit_provider_create__' in args[1]

    client.delete(f'/api/email-providers/{pid}', headers=headers)


def test_audit_called_on_provider_delete(client, headers):
    """Deleting an email provider must call log_provider_change('DELETED', ...)."""
    payload = {
        'name': '__audit_provider_delete__',
        'provider_type': 'smtp',
        'config': {'host': 'smtp.example.com', 'port': 587,
                   'username': 'u', 'password': 'p'},
    }
    resp = client.post('/api/email-providers', json=payload, headers=headers)
    pid = resp.get_json()['id']

    import flowforge.audit as audit_mod
    with patch.object(audit_mod, 'log_provider_change') as mock_log:
        del_resp = client.delete(f'/api/email-providers/{pid}', headers=headers)
        assert del_resp.status_code == 200

    mock_log.assert_called_once()
    assert mock_log.call_args[0][0] == 'DELETED'


# ── _JsonStdoutHandler ────────────────────────────────────────────────────────

def _make_log_record(message: str, level: int = logging.INFO) -> logging.LogRecord:
    record = logging.LogRecord(
        name='flowforge.audit',
        level=level,
        pathname='',
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    return record


def test_json_stdout_handler_writes_to_stdout():
    from flowforge.audit import _JsonStdoutHandler
    handler = _JsonStdoutHandler()
    buf = io.StringIO()
    with patch('sys.stdout', buf):
        handler.emit(_make_log_record('test message'))
    output = buf.getvalue()
    assert output.strip() != ''


def test_json_stdout_handler_output_is_valid_json():
    from flowforge.audit import _JsonStdoutHandler
    handler = _JsonStdoutHandler()
    buf = io.StringIO()
    with patch('sys.stdout', buf):
        handler.emit(_make_log_record('test message'))
    payload = json.loads(buf.getvalue().strip())
    assert isinstance(payload, dict)


def test_json_stdout_handler_contains_message():
    from flowforge.audit import _JsonStdoutHandler
    handler = _JsonStdoutHandler()
    buf = io.StringIO()
    with patch('sys.stdout', buf):
        handler.emit(_make_log_record('LOGIN SUCCESS user=alice'))
    payload = json.loads(buf.getvalue().strip())
    assert payload['message'] == 'LOGIN SUCCESS user=alice'


def test_json_stdout_handler_contains_level():
    from flowforge.audit import _JsonStdoutHandler
    handler = _JsonStdoutHandler()
    buf = io.StringIO()
    with patch('sys.stdout', buf):
        handler.emit(_make_log_record('msg', level=logging.INFO))
    payload = json.loads(buf.getvalue().strip())
    assert payload['level'] == 'INFO'


def test_json_stdout_handler_contains_logger_name():
    from flowforge.audit import _JsonStdoutHandler
    handler = _JsonStdoutHandler()
    buf = io.StringIO()
    with patch('sys.stdout', buf):
        handler.emit(_make_log_record('msg'))
    payload = json.loads(buf.getvalue().strip())
    assert payload['logger'] == 'flowforge.audit'


def test_json_stdout_handler_ts_is_utc_iso_format():
    from flowforge.audit import _JsonStdoutHandler
    import re
    handler = _JsonStdoutHandler()
    buf = io.StringIO()
    with patch('sys.stdout', buf):
        handler.emit(_make_log_record('msg'))
    payload = json.loads(buf.getvalue().strip())
    # Expect YYYY-MM-DDTHH:MM:SSZ
    assert re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', payload['ts']), payload['ts']


def test_json_stdout_handler_ends_with_newline():
    from flowforge.audit import _JsonStdoutHandler
    handler = _JsonStdoutHandler()
    buf = io.StringIO()
    with patch('sys.stdout', buf):
        handler.emit(_make_log_record('msg'))
    assert buf.getvalue().endswith('\n')


def test_json_stdout_handler_does_not_raise_on_broken_stdout():
    from flowforge.audit import _JsonStdoutHandler

    class BrokenStdout:
        def write(self, s):
            raise OSError('broken pipe')
        def flush(self):
            raise OSError('broken pipe')

    handler = _JsonStdoutHandler()
    with patch('sys.stdout', BrokenStdout()):
        handler.emit(_make_log_record('msg'))  # must not raise
