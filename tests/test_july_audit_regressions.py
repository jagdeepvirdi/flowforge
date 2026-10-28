"""Regression tests for the 2026-07-01 architect/VC audit findings.

Each section pins one finding so a future refactor cannot silently reopen it:

1. SQL injection through data_load identifiers (target_table / column names).
2. Secret pipeline variables leaking into SQL, email, notification and report sinks.
3. SSRF through editor-configurable outbound URLs (notification steps, failure webhook).
4. User-administration events filed under PIPELINE_CFG_* instead of USER_*.

Sections 1–3 are unit-level (mocked connections / sockets); section 4 uses the API + test DB.
"""
from unittest.mock import MagicMock, patch

import pytest

from flowforge.engine.step_exec import _run_step_with_retry
from flowforge.steps.base import StepResult

# ═════════════════════════════════════════════════════════════════════════════
# 1. data_load SQL injection
# ═════════════════════════════════════════════════════════════════════════════

_BAD_IDENTIFIERS = [
    'users; DROP TABLE accounts',
    'users--',
    "users' OR '1'='1",
    'users WHERE 1=1',
    'users(id)',
    '"quoted"',
    'a b',
    'users\nDROP TABLE x',
    '1; SELECT pg_sleep(10)',
]


def _data_load(config):
    from flowforge.steps.data_load import DataLoadStep
    return DataLoadStep(name='load', config=config)


def _write_csv(tmp_path, header, row):
    p = tmp_path / 'in.csv'
    p.write_text(f'{header}\n{row}\n', encoding='utf-8')
    return str(p)


def _mock_conn():
    conn = MagicMock()
    conn.db_type = 'postgresql'
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.make_placeholders.return_value = '%s'
    conn.execute_many.return_value = 1
    return conn


@pytest.mark.parametrize('table', _BAD_IDENTIFIERS)
def test_data_load_rejects_injection_in_target_table(table, tmp_path):
    step = _data_load({
        'target_connection_id': 'conn-1', 'target_table': table, 'mode': 'replace',
        'source': {'type': 'file', 'file_path': _write_csv(tmp_path, 'id', '1')},
    })
    with patch('flowforge.connections.factory.get_connection') as get_conn:
        result = step.run({})
    assert result.success is False
    assert 'target_table' in result.error
    get_conn.assert_not_called()


def test_data_load_rejects_injection_arriving_through_a_template_variable(tmp_path):
    """target_table is Jinja2-rendered, so the guard must run on the rendered value."""
    step = _data_load({
        'target_connection_id': 'conn-1', 'target_table': 'staging.{{ evil }}', 'mode': 'append',
        'source': {'type': 'file', 'file_path': _write_csv(tmp_path, 'id', '1')},
    })
    with patch('flowforge.connections.factory.get_connection') as get_conn:
        result = step.run({'evil': 'x; DROP TABLE users--'})
    assert result.success is False
    get_conn.assert_not_called()


@pytest.mark.parametrize('column', ['id; DROP TABLE users', 'a b', 'x--', "n'ame"])
def test_data_load_rejects_injection_in_source_column_names(column, tmp_path):
    step = _data_load({
        'target_connection_id': 'conn-1', 'target_table': 'staging.t', 'mode': 'append',
        'source': {'type': 'file', 'file_path': _write_csv(tmp_path, f'id,{column}', '1,2')},
    })
    with patch('flowforge.connections.factory.get_connection') as get_conn:
        result = step.run({})
    assert result.success is False
    assert 'column name' in result.error
    get_conn.assert_not_called()


def test_data_load_rejects_injection_introduced_by_column_map(tmp_path):
    step = _data_load({
        'target_connection_id': 'conn-1', 'target_table': 'staging.t', 'mode': 'append',
        'column_map': {'id': 'id); DROP TABLE users; --'},
        'source': {'type': 'file', 'file_path': _write_csv(tmp_path, 'id', '1')},
    })
    with patch('flowforge.connections.factory.get_connection') as get_conn:
        result = step.run({})
    assert result.success is False
    get_conn.assert_not_called()


def test_data_load_still_loads_with_valid_identifiers(tmp_path):
    """Positive control: the guard must not block ordinary schema-qualified names."""
    conn = _mock_conn()
    step = _data_load({
        'target_connection_id': 'conn-1', 'target_table': 'staging.sales_2026_05', 'mode': 'append',
        'source': {'type': 'file', 'file_path': _write_csv(tmp_path, 'id,amount', '1,2')},
    })
    with patch('flowforge.connections.factory.get_connection', return_value=conn):
        result = step.run({})
    assert result.success is True
    sql = conn.execute_many.call_args.args[0]
    assert sql.startswith('INSERT INTO staging.sales_2026_05 (id, amount)')


# ═════════════════════════════════════════════════════════════════════════════
# 2. Secret pipeline variables must not reach SQL / email / notification sinks
# ═════════════════════════════════════════════════════════════════════════════

_CANARY = 'canary-9f3a1c'
_GUARDED_CTX = {'canary_var': _CANARY, '_secret_var_keys': {'canary_var'}, 'steps': {}}


def _assert_blocked_without_leaking(result: StepResult):
    assert result.success is False
    assert 'canary_var' in result.error          # names the variable so the author can fix it…
    assert _CANARY not in result.error          # …but never echoes its value
    assert _CANARY not in (result.logs or '')


def test_db_query_blocks_secret_in_sql():
    from flowforge.steps.db_query import DbQueryStep
    step = DbQueryStep(name='q', config={'query': "SELECT '{{ canary_var }}'"})
    with patch('flowforge.connections.factory.get_connection') as get_conn:
        result = _run_step_with_retry('p', step, dict(_GUARDED_CTX), 0, 0)
    _assert_blocked_without_leaking(result)
    get_conn.assert_not_called()


def test_data_load_blocks_secret_in_source_query():
    step = _data_load({
        'target_connection_id': 'conn-1', 'target_table': 'staging.t', 'mode': 'append',
        'source': {'type': 'query', 'connection_id': 'src', 'query': "SELECT '{{ canary_var }}'"},
    })
    with patch('flowforge.connections.factory.get_connection') as get_conn:
        result = _run_step_with_retry('p', step, dict(_GUARDED_CTX), 0, 0)
    assert result.success is False
    assert _CANARY not in result.error
    get_conn.assert_not_called()


def test_report_blocks_secret_in_report_query():
    from flowforge.steps.report import ReportStep
    step = ReportStep(name='r', config={'report_config_id': 'x'})
    cfg = {'query': "SELECT '{{ canary_var }}'", 'format': 'csv', 'output_filename': 'o.csv'}
    with patch.object(ReportStep, '_load_config', return_value=cfg):
        result = _run_step_with_retry('p', step, dict(_GUARDED_CTX), 0, 0)
    _assert_blocked_without_leaking(result)


@pytest.mark.parametrize('field', ['message', 'title'])
def test_notification_blocks_secret_in_message_and_title(field):
    from flowforge.steps.notification import NotificationStep
    cfg = {'platform': 'slack', 'webhook_url': 'https://hooks.slack.com/services/T/B/X', 'message': 'ok'}
    cfg[field] = 'value={{ canary_var }}'
    step = NotificationStep(name='n', config=cfg)
    with patch('flowforge.net_guard.safe_urlopen') as urlopen:
        result = step.run(dict(_GUARDED_CTX))
    _assert_blocked_without_leaking(result)
    urlopen.assert_not_called()


def test_email_sinks_block_secret_in_subject_body_and_drive_message():
    """email_step renders subject/body/drive message through these two helpers."""
    from flowforge.engine.context import SecretLeakError, render_guarded, render_simple_document
    for tmpl in ('Report for {{ canary_var }}', 'Dear user, key is {{ canary_var }}'):
        with pytest.raises(SecretLeakError) as exc:
            render_guarded(tmpl, dict(_GUARDED_CTX), sink='email subject')
        assert _CANARY not in str(exc.value)
        with pytest.raises(SecretLeakError) as exc:
            render_simple_document(tmpl, dict(_GUARDED_CTX), sink='email body')
        assert _CANARY not in str(exc.value)


def test_non_secret_variables_still_render_in_every_sink():
    from flowforge.engine.context import render_guarded, render_simple_document, render_sql
    ctx = {'month': '2026-05', '_secret_var_keys': {'canary_var'}, 'canary_var': _CANARY, 'steps': {}}
    assert render_sql('SELECT {{ month }}', ctx) == 'SELECT 2026-05'
    assert render_guarded('{{ month }}', ctx) == '2026-05'
    assert '2026-05' in render_simple_document('{{ month }}', ctx)


# ═════════════════════════════════════════════════════════════════════════════
# 3. SSRF on outbound webhooks (real guard, real sockets blocked)
# ═════════════════════════════════════════════════════════════════════════════

_INTERNAL_URLS = [
    'http://169.254.169.254/latest/meta-data/',   # cloud metadata
    'http://127.0.0.1:8080/hook',                 # loopback
    'http://10.0.0.5/hook',                       # RFC1918
    'http://192.168.1.10/hook',
    'http://[::1]/hook',                          # IPv6 loopback
    'http://localhost/hook',
]


@pytest.fixture
def no_network():
    """Fail the test if anything actually tries to open a TCP connection."""
    attempts = []

    def _connect(self, address, *a, **kw):
        attempts.append(address)
        raise OSError('network disabled in test')

    with patch('socket.socket.connect', _connect):
        yield attempts


@pytest.mark.parametrize('platform', ['slack', 'teams'])
@pytest.mark.parametrize('url', _INTERNAL_URLS)
def test_notification_never_connects_to_internal_addresses(platform, url, no_network):
    from flowforge.steps.notification import NotificationStep
    step = NotificationStep(name='n', config={'platform': platform, 'webhook_url': url, 'message': 'hi'})
    result = step.run({'steps': {}})
    assert result.success is False
    assert no_network == []


@pytest.mark.parametrize('url', _INTERNAL_URLS)
def test_failure_webhook_never_connects_to_internal_addresses(url, no_network):
    from flowforge.engine.notifications import _fire_failure_webhook
    _fire_failure_webhook(url, {'pipeline_name': 'p'})   # must swallow the refusal, not raise
    assert no_network == []


@pytest.mark.parametrize('url', [u for u in _INTERNAL_URLS if 'localhost' not in u])
def test_failure_webhook_literal_internal_ip_rejected_at_save_time(url):
    from flowforge.api.validators import validate_pipeline
    err = validate_pipeline({'name': 'p', 'on_failure_webhook_url': url})
    assert err is not None


def test_failure_webhook_hostnames_are_not_resolved_at_save_time():
    """By design: names are checked at send time (DNS can change), which the
    never-connects tests above enforce — save time only rejects literal IPs/schemes."""
    from flowforge.api.validators import validate_pipeline
    assert validate_pipeline({'name': 'p', 'on_failure_webhook_url': 'http://localhost/hook'}) is None


def test_failure_webhook_url_must_be_http_or_https():
    from flowforge.api.validators import validate_pipeline
    assert validate_pipeline({'name': 'p', 'on_failure_webhook_url': 'file:///etc/passwd'}) is not None
    assert validate_pipeline({'name': 'p', 'on_failure_webhook_url': 'gopher://example.com/'}) is not None


# ═════════════════════════════════════════════════════════════════════════════
# 4. User-admin events are filed as USER_*, not PIPELINE_CFG_*
# ═════════════════════════════════════════════════════════════════════════════


def _audit_actions(app, name):
    from flowforge.db.models import AuditLog, db
    with app.app_context():
        rows = db.session.query(AuditLog).all()
        return [r.action for r in rows if (r.details or {}).get('name') == name]


def test_user_create_update_delete_are_audited_as_user_events(app, client, headers):
    name = 'audit_regress_user'
    resp = client.post('/api/users', json={'username': name, 'password': 'Pass1234!', 'role': 'editor'},
                       headers=headers)
    assert resp.status_code == 201
    uid = resp.get_json()['id']
    assert client.patch(f'/api/users/{uid}', json={'role': 'viewer'}, headers=headers).status_code == 200
    assert client.delete(f'/api/users/{uid}', headers=headers).status_code in (200, 204)

    actions = _audit_actions(app, name)
    assert {'USER_CREATED', 'USER_UPDATED', 'USER_DELETED'} <= set(actions)
    assert not [a for a in actions if a.startswith('PIPELINE_CFG_')]


def test_log_user_change_does_not_use_pipeline_prefix():
    from flowforge import audit
    with patch.object(audit, '_write_db_audit') as write, patch.object(audit, '_get_logger'):
        audit.log_user_change('created', 'alice', 'uid-1')
    assert write.call_args.args[0] == 'USER_CREATED'
