"""Tests for Jinja2 variable resolution in engine/context.py."""
import re
from datetime import datetime, timedelta

import pytest


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
    monkeypatch.setenv('TEST_REGION', 'hello123')
    ctx = build('test')
    result = render('{{ env.TEST_REGION }}', ctx)
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


# ── _SafeEnv: newly-added credential vars + name-pattern defense-in-depth ────
# Regression coverage for the 2026-07-06 fix: PR #94's bulk-load preview
# endpoint let any authenticated user exfiltrate any env var not in the (then
# 7-entry) blocklist via a crafted `{{ env.X }}` template, e.g. FLOWFORGE_DB_URL,
# AWS_SECRET_ACCESS_KEY. The blocklist was expanded and a name-pattern check
# added so the *next* credential-shaped env var is blocked by default too.

@pytest.mark.parametrize('var_name', [
    'FLOWFORGE_DB_URL',
    'FLOWFORGE_REDIS_URL',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'AZURE_STORAGE_ACCOUNT_KEY',
    'AZURE_STORAGE_CONNECTION_STRING',
    'GOOGLE_SSO_CLIENT_SECRET',
    'MICROSOFT_SSO_CLIENT_SECRET',
    'SAML_IDP_X509_CERT',
    'DB_PASSWORD',
])
def test_safe_env_blocks_newly_added_credential_vars(monkeypatch, var_name):
    monkeypatch.setenv(var_name, 'must-not-leak')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render(f'{{{{ env.{var_name} }}}}', ctx) == ''


@pytest.mark.parametrize('var_name', [
    'SOME_FUTURE_SECRET',
    'SOME_FUTURE_PASSWORD',
    'SOME_FUTURE_TOKEN',
    'SOME_FUTURE_API_KEY',
    'SOME_FUTURE_CERT',
    'SOME_FUTURE_CONNECTION_STRING',
    'SOME_FUTURE_DSN',
    'SOME_FUTURE_DB_URL',
])
def test_safe_env_blocks_unlisted_credential_shaped_names(monkeypatch, var_name):
    """A credential-shaped name blocked by the keyword pattern even though it's
    not (and can never exhaustively be) in the explicit _ENV_BLOCKLIST."""
    monkeypatch.setenv(var_name, 'must-not-leak')
    from flowforge.engine.context import build, render
    ctx = build('test')
    assert render(f'{{{{ env.{var_name} }}}}', ctx) == ''


def test_safe_env_pattern_does_not_block_ordinary_names():
    from flowforge.engine.context import _looks_like_credential_name
    for name in ('APP_ENV', 'REPORT_DIR', 'DB_HOST', 'OLLAMA_QUERY_MODEL', 'FLOWFORGE_PORT'):
        assert not _looks_like_credential_name(name), name


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


# ── render_sql / render_guarded — secret-in-SQL hard block ────────────────────

def test_render_sql_works_like_render_for_normal_vars():
    from flowforge.engine.context import build, render_sql
    ctx = build('test', pipeline_vars={'report_date': '2026-05'})
    ctx['_secret_var_keys'] = set()
    result = render_sql('SELECT * FROM t WHERE month = {{ report_date }}', ctx)
    assert '2026-05' in result


def test_render_sql_blocks_secret_vars():
    """Secret vars must never render into SQL text — hard block, not warn."""
    from flowforge.engine.context import SecretLeakError, build, render_sql
    ctx = build('test', pipeline_vars={'MY_SECRET': 'topsecret'})
    ctx['_secret_var_keys'] = {'MY_SECRET'}
    with pytest.raises(SecretLeakError):
        render_sql("SELECT '{{ MY_SECRET }}'", ctx)


def test_render_sql_error_names_the_secret_key():
    from flowforge.engine.context import SecretLeakError, build, render_sql
    ctx = build('test', pipeline_vars={'DB_PASS': 's3cr3t'})
    ctx['_secret_var_keys'] = {'DB_PASS'}
    with pytest.raises(SecretLeakError) as exc_info:
        render_sql("SELECT * FROM t WHERE pass = '{{ DB_PASS }}'", ctx)
    assert 'DB_PASS' in str(exc_info.value)


def test_render_sql_does_not_block_non_secret_vars():
    from flowforge.engine.context import build, render_sql
    ctx = build('test', pipeline_vars={'report_month': '2026-05'})
    ctx['_secret_var_keys'] = {'MY_OTHER_SECRET'}  # different key
    result = render_sql('SELECT * FROM t WHERE month = {{ report_month }}', ctx)
    assert '2026-05' in result


def test_render_sql_no_secret_keys_in_context():
    """render_sql must not crash when _secret_var_keys is absent from context."""
    from flowforge.engine.context import build, render_sql
    ctx = build('test')
    # _secret_var_keys not set
    result = render_sql('SELECT 1', ctx)
    assert result == 'SELECT 1'


def test_render_sql_blocks_multiple_secrets():
    from flowforge.engine.context import SecretLeakError, build, render_sql
    ctx = build('test', pipeline_vars={'KEY1': 'a', 'KEY2': 'b'})
    ctx['_secret_var_keys'] = {'KEY1', 'KEY2'}
    with pytest.raises(SecretLeakError) as exc_info:
        render_sql("SELECT '{{ KEY1 }}', '{{ KEY2 }}'", ctx)
    msg = str(exc_info.value)
    assert 'KEY1' in msg or 'KEY2' in msg


def test_render_guarded_blocks_secret_in_email_sink():
    from flowforge.engine.context import SecretLeakError, build, render_guarded
    ctx = build('test', pipeline_vars={'API_KEY': 'xyz'})
    ctx['_secret_var_keys'] = {'API_KEY'}
    with pytest.raises(SecretLeakError):
        render_guarded('Your key is {{ API_KEY }}', ctx, sink='email body')


def test_render_guarded_allows_non_secret_vars():
    from flowforge.engine.context import build, render_guarded
    ctx = build('test', pipeline_vars={'report_month': '2026-05'})
    ctx['_secret_var_keys'] = set()
    result = render_guarded('Report for {{ report_month }}', ctx, sink='email body')
    assert 'Report for 2026-05' == result


# ── text_to_html (simple document email body format) ──────────────────────────

def test_text_to_html_single_paragraph():
    from flowforge.engine.context import text_to_html
    assert text_to_html('Hello there') == '<p>Hello there</p>'


def test_text_to_html_blank_line_starts_new_paragraph():
    from flowforge.engine.context import text_to_html
    result = text_to_html('First paragraph.\n\nSecond paragraph.')
    assert result == '<p>First paragraph.</p>\n<p>Second paragraph.</p>'


def test_text_to_html_single_newline_becomes_br():
    from flowforge.engine.context import text_to_html
    result = text_to_html('Line one\nLine two')
    assert result == '<p>Line one<br>\nLine two</p>'


def test_text_to_html_escapes_special_characters():
    from flowforge.engine.context import text_to_html
    result = text_to_html('Tom & Jerry <script>alert(1)</script>')
    assert '&amp;' in result
    assert '&lt;script&gt;' in result
    assert '<script>' not in result


def test_text_to_html_skips_blank_paragraphs():
    from flowforge.engine.context import text_to_html
    result = text_to_html('First.\n\n\n\nSecond.')
    assert result == '<p>First.</p>\n<p>Second.</p>'


# ── render_simple_document (simple document format + safe HTML fragments) ─────

def test_render_simple_document_escapes_literal_text():
    from flowforge.engine.context import build, render_simple_document
    ctx = build('test')
    ctx['_secret_var_keys'] = set()
    result = render_simple_document('Tom & Jerry <script>alert(1)</script>', ctx)
    assert '&amp;' in result
    assert '&lt;script&gt;' in result
    assert '<script>' not in result


def test_render_simple_document_wraps_paragraphs():
    from flowforge.engine.context import build, render_simple_document
    ctx = build('test')
    ctx['_secret_var_keys'] = set()
    result = render_simple_document('Hi there,\n\nSecond line.', ctx)
    assert result == '<p>Hi there,</p>\n<p>Second line.</p>'


def test_render_simple_document_preserves_step_table_html():
    """A step's table_html/kv_html must render as real markup, not escaped
    source text, even in the "Simple document" (plain-text) body format."""
    from flowforge.engine.context import build, render_simple_document
    ctx = build('test', step_results={
        'query': {'table_html': '<table><tr><td>1</td></tr></table>', 'kv_html': ''},
    })
    ctx['_secret_var_keys'] = set()
    result = render_simple_document('Results:\n\n{{ steps.query.table_html }}', ctx)
    assert '<table><tr><td>1</td></tr></table>' in result
    assert '&lt;table&gt;' not in result


def test_render_simple_document_escapes_text_around_table_html():
    from flowforge.engine.context import build, render_simple_document
    ctx = build('test', step_results={
        'query': {'table_html': '<table></table>', 'kv_html': ''},
    })
    ctx['_secret_var_keys'] = set()
    result = render_simple_document('A < B {{ steps.query.table_html }} C & D', ctx)
    assert 'A &lt; B <table></table> C &amp; D' in result
