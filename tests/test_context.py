"""Tests for Jinja2 variable resolution in engine/context.py."""
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
    import uuid

    from flowforge.engine.context import build
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
    import calendar

    from flowforge.engine.context import build
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


# ── _SafeEnv allowlist mode ───────────────────────────────────────────────────

def test_safe_env_allowlist_permits_listed_var(monkeypatch):
    """When allowlist is set, a listed var is accessible."""
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', 'REPORT_DIR')
    monkeypatch.setenv('REPORT_DIR', '/data/reports')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.REPORT_DIR }}', ctx) == '/data/reports'


def test_safe_env_allowlist_blocks_unlisted_var(monkeypatch):
    """When allowlist is set, an unlisted var is blocked even if it exists."""
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', 'REPORT_DIR')
    monkeypatch.setenv('DB_HOST', 'myhost')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.DB_HOST }}', ctx) == ''


def test_safe_env_allowlist_blocks_credential_vars(monkeypatch):
    """When allowlist is set, credential vars not in the list are blocked."""
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', 'REPORT_DIR')
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', 'should-not-leak')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.FLOWFORGE_SECRET_KEY }}', ctx) == ''


def test_safe_env_allowlist_multiple_vars(monkeypatch):
    """All vars in a comma-separated allowlist are accessible."""
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', 'VAR_A,VAR_B,VAR_C')
    monkeypatch.setenv('VAR_A', 'alpha')
    monkeypatch.setenv('VAR_B', 'beta')
    monkeypatch.setenv('VAR_C', 'gamma')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.VAR_A }}', ctx) == 'alpha'
    assert render('{{ env.VAR_B }}', ctx) == 'beta'
    assert render('{{ env.VAR_C }}', ctx) == 'gamma'


def test_safe_env_allowlist_spaces_trimmed(monkeypatch):
    """Spaces around var names in the allowlist are trimmed."""
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', '  VAR_X ,  VAR_Y  ')
    monkeypatch.setenv('VAR_X', 'x-value')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.VAR_X }}', ctx) == 'x-value'


def test_safe_env_allowlist_missing_var_returns_empty(monkeypatch):
    """An allowlisted var that isn't in os.environ returns empty string."""
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', 'NONEXISTENT_XYZ_123')
    monkeypatch.delenv('NONEXISTENT_XYZ_123', raising=False)
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.NONEXISTENT_XYZ_123 }}', ctx) == ''


def test_safe_env_allowlist_empty_string_falls_back_to_blocklist(monkeypatch):
    """Empty FLOWFORGE_TEMPLATE_ENV_VARS falls back to blocklist mode."""
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', '')
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', 'must-not-leak')
    monkeypatch.setenv('SAFE_CUSTOM_VAR', 'visible')
    from flowforge.engine.context import build, render
    ctx = build('test')
    # Blocklist mode: FLOWFORGE_SECRET_KEY is blocked, safe var is visible
    assert render('{{ env.FLOWFORGE_SECRET_KEY }}', ctx) == ''
    assert render('{{ env.SAFE_CUSTOM_VAR }}', ctx) == 'visible'


def test_safe_env_allowlist_credential_explicitly_listed(monkeypatch):
    """If a credential is explicitly in the allowlist, it IS accessible.

    This is intentional — allowlist mode is opt-in and explicit.
    """
    monkeypatch.setenv('FLOWFORGE_TEMPLATE_ENV_VARS', 'REPORT_DIR,MY_CUSTOM_KEY')
    monkeypatch.setenv('MY_CUSTOM_KEY', 'custom-value')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render('{{ env.MY_CUSTOM_KEY }}', ctx) == 'custom-value'


# ── render_sql — SEC-3 secret-in-SQL detection ────────────────────────────────

def test_render_sql_works_like_render_for_normal_vars():
    from flowforge.engine.context import build, render_sql
    ctx = build('test', pipeline_vars={'report_date': '2026-05'})
    ctx['_secret_var_keys'] = set()
    result = render_sql('SELECT * FROM t WHERE month = {{ report_date }}', ctx)
    assert '2026-05' in result


def test_render_sql_still_renders_secret_vars(caplog):
    """Secret vars still render — render_sql is warn-only, not blocking."""
    from flowforge.engine.context import build, render_sql
    ctx = build('test', pipeline_vars={'MY_SECRET': 'topsecret'})
    ctx['_secret_var_keys'] = {'MY_SECRET'}
    result = render_sql("SELECT '{{ MY_SECRET }}'", ctx)
    assert 'topsecret' in result


def test_render_sql_logs_warning_for_secret_in_sql(caplog):
    import logging

    from flowforge.engine.context import build, render_sql
    ctx = build('test', pipeline_vars={'DB_PASS': 's3cr3t'})
    ctx['_secret_var_keys'] = {'DB_PASS'}
    with caplog.at_level(logging.WARNING, logger='flowforge.engine.context'):
        render_sql("SELECT * FROM t WHERE pass = '{{ DB_PASS }}'", ctx)
    assert any('DB_PASS' in r.message for r in caplog.records)
    assert any('secret' in r.message.lower() for r in caplog.records)


def test_render_sql_no_warning_for_non_secret_vars(caplog):
    import logging

    from flowforge.engine.context import build, render_sql
    ctx = build('test', pipeline_vars={'report_month': '2026-05'})
    ctx['_secret_var_keys'] = {'MY_OTHER_SECRET'}  # different key
    with caplog.at_level(logging.WARNING, logger='flowforge.engine.context'):
        render_sql('SELECT * FROM t WHERE month = {{ report_month }}', ctx)
    # No warning about non-secret var
    assert not any('report_month' in r.message for r in caplog.records)


def test_render_sql_no_secret_keys_in_context():
    """render_sql must not crash when _secret_var_keys is absent from context."""
    from flowforge.engine.context import build, render_sql
    ctx = build('test')
    # _secret_var_keys not set
    result = render_sql('SELECT 1', ctx)
    assert result == 'SELECT 1'


def test_render_sql_warns_for_multiple_secrets(caplog):
    import logging

    from flowforge.engine.context import build, render_sql
    ctx = build('test', pipeline_vars={'KEY1': 'a', 'KEY2': 'b'})
    ctx['_secret_var_keys'] = {'KEY1', 'KEY2'}
    with caplog.at_level(logging.WARNING, logger='flowforge.engine.context'):
        render_sql("SELECT '{{ KEY1 }}', '{{ KEY2 }}'", ctx)
    msgs = ' '.join(r.message for r in caplog.records)
    assert 'KEY1' in msgs or 'KEY2' in msgs
