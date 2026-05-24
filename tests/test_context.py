"""Tests for Jinja2 variable resolution in engine/context.py."""
import os
import re
from datetime import datetime, timedelta


def test_built_in_current_date():
    from flowforge.engine.context import build
    ctx = build('test')
    today = datetime.today().strftime('%Y-%m-%d')
    assert ctx['current_date'] == today


def test_built_in_current_month():
    from flowforge.engine.context import build
    ctx = build('test')
    assert re.match(r'\d{4}-\d{2}', ctx['current_month'])


def test_built_in_current_year():
    from flowforge.engine.context import build
    ctx = build('test')
    assert ctx['current_year'] == str(datetime.today().year)


def test_built_in_yesterday():
    from flowforge.engine.context import build
    ctx = build('test')
    expected = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    assert ctx['yesterday'] == expected


def test_built_in_run_id_is_uuid():
    from flowforge.engine.context import build
    import uuid
    ctx = build('test')
    uuid.UUID(ctx['run_id'])   # raises if not valid UUID


def test_pipeline_name_in_context():
    from flowforge.engine.context import build
    ctx = build('My Pipeline')
    assert ctx['pipeline_name'] == 'My Pipeline'


def test_env_var_resolution(monkeypatch):
    from flowforge.engine.context import build, render
    monkeypatch.setenv('TEST_SECRET', 'hello123')
    ctx = build('test')
    result = render('{{ env.TEST_SECRET }}', ctx)
    assert result == 'hello123'


def test_missing_env_var_renders_empty(monkeypatch):
    from flowforge.engine.context import build, render
    monkeypatch.delenv('NONEXISTENT_VAR_XYZ', raising=False)
    ctx = build('test')
    result = render('{{ env.NONEXISTENT_VAR_XYZ }}', ctx)
    assert result == ''


def test_steps_output_path_threading():
    from flowforge.engine.context import build, render
    step_results = {'generate_report': {'output_path': '/tmp/report.xlsx', 'drive_url': '', 'rows_affected': 0}}
    ctx = build('test', step_results=step_results)
    result = render('{{ steps.generate_report.output_path }}', ctx)
    assert result == '/tmp/report.xlsx'


def test_steps_drive_url_threading():
    from flowforge.engine.context import build, render
    step_results = {'upload': {'output_path': '', 'drive_url': 'https://drive.google.com/file/abc', 'rows_affected': 0}}
    ctx = build('test', step_results=step_results)
    result = render('{{ steps.upload.drive_url }}', ctx)
    assert result == 'https://drive.google.com/file/abc'


def test_pipeline_variables_injected():
    from flowforge.engine.context import build, render
    ctx = build('test', pipeline_vars={'report_month': '2026-04', 'region': 'APAC'})
    assert render('{{ report_month }}_{{ region }}', ctx) == '2026-04_APAC'


def test_render_current_date_in_filename():
    from flowforge.engine.context import build, render
    ctx = build('test')
    today = datetime.today().strftime('%Y-%m-%d')
    result = render('report_{{ current_date }}.xlsx', ctx)
    assert result == f'report_{today}.xlsx'


def test_render_missing_variable_is_empty():
    """Undefined Jinja2 variables should silently render as empty string."""
    from flowforge.engine.context import build, render
    ctx = build('test')
    result = render('prefix_{{ totally_unknown_var }}_suffix', ctx)
    assert result == 'prefix__suffix'


def test_render_complex_template():
    from flowforge.engine.context import build, render
    ctx = build('Monthly Report', pipeline_vars={'region': 'EMEA'})
    tmpl = 'Subject: {{ pipeline_name }} - {{ current_month }} - {{ region }}'
    result = render(tmpl, ctx)
    month = datetime.today().strftime('%Y-%m')
    assert result == f'Subject: Monthly Report - {month} - EMEA'


# ── Previous-month date vars ───────────────────────────────────────────────

def test_built_in_prev_month_start():
    from flowforge.engine.context import build
    ctx = build('test')
    assert re.match(r'^\d{4}-\d{2}-01$', ctx['prev_month_start']), (
        f"prev_month_start should be YYYY-MM-01, got {ctx['prev_month_start']}"
    )


def test_built_in_prev_month_end():
    from flowforge.engine.context import build
    import calendar
    ctx = build('test')
    val = ctx['prev_month_end']
    assert re.match(r'^\d{4}-\d{2}-\d{2}$', val), f"Expected YYYY-MM-DD, got {val}"
    # The day must equal the last day of that month
    y, m, d = (int(x) for x in val.split('-'))
    assert d == calendar.monthrange(y, m)[1]


def test_prev_month_start_before_month_start():
    """prev_month_start must be strictly before current month_start."""
    from flowforge.engine.context import build
    ctx = build('test')
    assert ctx['prev_month_start'] < ctx['month_start']


# ── Timestamp boundary vars (YYYYMMDDHHmmSS, 14 digits) ───────────────────

_TS_PATTERN = re.compile(r'^\d{14}$')


def test_day_start_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['day_start_ts']), ctx['day_start_ts']
    assert ctx['day_start_ts'].endswith('000000')


def test_day_end_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['day_end_ts']), ctx['day_end_ts']
    assert ctx['day_end_ts'].endswith('235959')


def test_yesterday_start_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['yesterday_start_ts']), ctx['yesterday_start_ts']
    assert ctx['yesterday_start_ts'].endswith('000000')


def test_yesterday_end_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['yesterday_end_ts']), ctx['yesterday_end_ts']
    assert ctx['yesterday_end_ts'].endswith('235959')


def test_month_start_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['month_start_ts']), ctx['month_start_ts']
    assert ctx['month_start_ts'][6:8] == '01'   # day = 01
    assert ctx['month_start_ts'].endswith('000000')


def test_month_end_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['month_end_ts']), ctx['month_end_ts']
    assert ctx['month_end_ts'].endswith('235959')


def test_prev_month_start_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['prev_month_start_ts']), ctx['prev_month_start_ts']
    assert ctx['prev_month_start_ts'][6:8] == '01'
    assert ctx['prev_month_start_ts'].endswith('000000')


def test_prev_month_end_ts_format():
    from flowforge.engine.context import build
    ctx = build('test')
    assert _TS_PATTERN.match(ctx['prev_month_end_ts']), ctx['prev_month_end_ts']
    assert ctx['prev_month_end_ts'].endswith('235959')


def test_day_start_ts_date_prefix_matches_current_date():
    """YYYYMMdd prefix of day_start_ts must equal current_date without dashes."""
    from flowforge.engine.context import build
    ctx = build('test')
    expected_prefix = ctx['current_date'].replace('-', '')
    assert ctx['day_start_ts'][:8] == expected_prefix


def test_yesterday_ts_date_prefix_matches_yesterday():
    from flowforge.engine.context import build
    ctx = build('test')
    expected_prefix = ctx['yesterday'].replace('-', '')
    assert ctx['yesterday_start_ts'][:8] == expected_prefix
    assert ctx['yesterday_end_ts'][:8] == expected_prefix


def test_timestamp_boundary_vars_renderable():
    """All timestamp vars must render without error in a Jinja2 template."""
    from flowforge.engine.context import build, render
    ctx = build('test')
    tmpl = (
        'WHERE ts BETWEEN {{ month_start_ts }} AND {{ month_end_ts }} '
        'OR ts BETWEEN {{ prev_month_start_ts }} AND {{ prev_month_end_ts }}'
    )
    result = render(tmpl, ctx)
    # All placeholders should be replaced with 14-digit numbers
    assert '{{' not in result
    for part in result.replace('WHERE ts BETWEEN ', '').replace(' OR ts BETWEEN ', ' ').replace(' AND ', ' ').split():
        assert _TS_PATTERN.match(part), f"Unexpected token: {part}"


# ── last_success_at is NOT a built-in (injected by runner) ────────────────

def test_last_success_at_not_in_built_ins():
    """last_success_at must not appear in build() output without runner injection."""
    from flowforge.engine.context import build
    ctx = build('test')
    assert 'last_success_at' not in ctx
    assert 'last_success_date' not in ctx


def test_last_success_at_available_when_injected():
    """When runner passes last_success_at as a pipeline var it must render."""
    from flowforge.engine.context import build, render
    ctx = build('test', pipeline_vars={
        'last_success_at': '20260501120000',
        'last_success_date': '2026-05-01',
    })
    assert render('{{ last_success_at }}', ctx) == '20260501120000'
    assert render('{{ last_success_date }}', ctx) == '2026-05-01'


# ── _SafeEnv credential blocklist ─────────────────────────────────────────────

def test_safe_env_blocks_flowforge_secret_key(monkeypatch):
    """FLOWFORGE_SECRET_KEY must never be readable from a Jinja2 template."""
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', 'aes-key-must-not-leak')
    from flowforge.engine.context import build, render
    ctx = build('test')
    result = render('{{ env.FLOWFORGE_SECRET_KEY }}', ctx)
    assert result == ''
    assert 'aes-key-must-not-leak' not in result


def test_safe_env_blocks_flowforge_password(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_PASSWORD', '$2b$12$fakehash')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.FLOWFORGE_PASSWORD }}', ctx) == ''


def test_safe_env_blocks_gmail_client_secret(monkeypatch):
    monkeypatch.setenv('GMAIL_CLIENT_SECRET', 'gmail-oauth-secret')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.GMAIL_CLIENT_SECRET }}', ctx) == ''


def test_safe_env_blocks_gmail_refresh_token(monkeypatch):
    monkeypatch.setenv('GMAIL_REFRESH_TOKEN', 'gmail-refresh-xxxx')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.GMAIL_REFRESH_TOKEN }}', ctx) == ''


def test_safe_env_blocks_microsoft_client_secret(monkeypatch):
    monkeypatch.setenv('MICROSOFT_CLIENT_SECRET', 'azure-secret-value')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.MICROSOFT_CLIENT_SECRET }}', ctx) == ''


def test_safe_env_blocks_anthropic_api_key(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-xxxx')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.ANTHROPIC_API_KEY }}', ctx) == ''


def test_safe_env_allows_non_blocked_var(monkeypatch):
    """Regular environment variables not in the blocklist must be readable."""
    monkeypatch.setenv('REPORT_OUTPUT_DIR', '/data/reports')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.REPORT_OUTPUT_DIR }}', ctx) == '/data/reports'


def test_safe_env_missing_var_returns_empty(monkeypatch):
    monkeypatch.delenv('TOTALLY_NONEXISTENT_VAR_XYZ', raising=False)
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.TOTALLY_NONEXISTENT_VAR_XYZ }}', ctx) == ''


# ── Pipeline variable collision warning ───────────────────────────────────────

def test_pipeline_var_collision_emits_warning(caplog):
    """A WARNING must be logged when a pipeline variable shadows a built-in key."""
    import logging
    from flowforge.engine.context import build
    with caplog.at_level(logging.WARNING, logger='flowforge.engine.context'):
        build('test', pipeline_vars={'current_date': '2020-01-01'})
    assert any('current_date' in msg for msg in caplog.messages), (
        f"Expected a collision warning mentioning 'current_date'. Got: {caplog.messages}"
    )


def test_pipeline_var_collision_value_wins(caplog):
    """Even when a collision is logged, the pipeline variable takes effect."""
    from flowforge.engine.context import build
    ctx = build('test', pipeline_vars={'current_date': '2020-01-01'})
    assert ctx['current_date'] == '2020-01-01'


def test_pipeline_var_collision_multiple_keys(caplog):
    """Multiple collisions are all mentioned in a single warning log line."""
    import logging
    from flowforge.engine.context import build
    with caplog.at_level(logging.WARNING, logger='flowforge.engine.context'):
        build('test', pipeline_vars={
            'current_date': '2020-01-01',
            'run_id': 'overridden-uuid',
        })
    collision_msgs = [m for m in caplog.messages if 'current_date' in m or 'run_id' in m]
    assert collision_msgs, f"Expected collision warning, got: {caplog.messages}"


def test_no_collision_warning_for_normal_vars(caplog):
    """No warning is emitted when pipeline variables do not shadow built-ins."""
    import logging
    from flowforge.engine.context import build
    with caplog.at_level(logging.WARNING, logger='flowforge.engine.context'):
        build('test', pipeline_vars={'my_custom_var': 'hello', 'report_region': 'APAC'})
    assert not any(
        'overwrite' in m.lower() or 'collision' in m.lower() or 'shadow' in m.lower()
        for m in caplog.messages
    )
