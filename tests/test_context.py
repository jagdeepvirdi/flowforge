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
