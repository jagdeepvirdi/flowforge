"""Tests for reports/excel_report.py — column formats, conditionals, template mode."""
import pytest
from pathlib import Path


def test_generate_basic(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'basic.xlsx'
    generate(
        rows=[(1, 'Alice', 100.0), (2, 'Bob', -50.0)],
        columns=['ID', 'Name', 'Amount'],
        output_path=out,
    )
    assert out.exists()
    assert out.stat().st_size > 0


def test_generate_creates_parent_dirs(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'nested' / 'deep' / 'report.xlsx'
    generate(rows=[(1,)], columns=['Col'], output_path=out)
    assert out.exists()


def test_generate_with_number_format(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'fmt.xlsx'
    generate(
        rows=[(1234567.89,)],
        columns=['Revenue'],
        output_path=out,
        column_formats=[{'column': 'Revenue', 'number_format': '#,##0.00'}],
    )
    assert out.exists()


def test_generate_with_explicit_column_width(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'width.xlsx'
    generate(
        rows=[('short',)],
        columns=['Description'],
        output_path=out,
        column_formats=[{'column': 'Description', 'width': 30}],
    )
    assert out.exists()


def test_generate_conditional_fill_lt(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'cond.xlsx'
    generate(
        rows=[(100,), (-5,), (0,)],
        columns=['Value'],
        output_path=out,
        column_formats=[{
            'column': 'Value',
            'conditional': [
                {'operator': 'lt', 'value': 0, 'bg_color': 'FFC7CE', 'font_color': '9C0006'},
            ],
        }],
    )
    assert out.exists()


def test_generate_conditional_all_operators(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'ops.xlsx'
    generate(
        rows=[(10,), (5,), (0,), (15,)],
        columns=['Score'],
        output_path=out,
        column_formats=[{
            'column': 'Score',
            'conditional': [
                {'operator': 'lte', 'value': 0,  'bg_color': 'FF0000'},
                {'operator': 'gte', 'value': 15, 'bg_color': '00FF00'},
                {'operator': 'eq',  'value': 5,  'bg_color': 'FFFF00'},
                {'operator': 'ne',  'value': 10, 'bg_color': 'AAAAAA'},
                {'operator': 'gt',  'value': 9,  'bg_color': '0000FF'},
            ],
        }],
    )
    assert out.exists()


def test_generate_conditional_non_numeric_value_skipped(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'nonnum.xlsx'
    generate(
        rows=[('not-a-number',)],
        columns=['Col'],
        output_path=out,
        column_formats=[{
            'column': 'Col',
            'conditional': [{'operator': 'lt', 'value': 0, 'bg_color': 'FF0000'}],
        }],
    )
    assert out.exists()


def test_generate_unknown_operator_skipped(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'badop.xlsx'
    generate(
        rows=[(5,)],
        columns=['Val'],
        output_path=out,
        column_formats=[{
            'column': 'Val',
            'conditional': [{'operator': 'unknown_op', 'value': 0, 'bg_color': 'FF0000'}],
        }],
    )
    assert out.exists()


def test_generate_with_template(tmp_path):
    """When a template .xlsx exists, rows are appended after the last row."""
    from openpyxl import Workbook
    from flowforge.reports.excel_report import generate

    # Build a minimal template
    tmpl = tmp_path / 'template.xlsx'
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Name', 'Amount'])
    wb.save(tmpl)

    out = tmp_path / 'from_template.xlsx'
    generate(
        rows=[(1, 'Alice', 100.0)],
        columns=['ID', 'Name', 'Amount'],
        output_path=out,
        template_path=tmpl,
        column_formats=[{'column': 'Amount', 'number_format': '#,##0.00'}],
    )
    assert out.exists()


def test_generate_template_path_not_exist_falls_back(tmp_path):
    """Non-existent template path causes fallback to a fresh workbook."""
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'fallback.xlsx'
    generate(
        rows=[(1, 'x')],
        columns=['ID', 'Val'],
        output_path=out,
        template_path=tmp_path / 'does_not_exist.xlsx',
    )
    assert out.exists()


def test_generate_empty_rows(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'empty.xlsx'
    generate(rows=[], columns=['Col1', 'Col2'], output_path=out)
    assert out.exists()


def test_matches_rule_all_operators():
    from flowforge.reports.excel_report import _matches_rule
    assert _matches_rule(5, {'operator': 'lt',  'value': 10})
    assert _matches_rule(10, {'operator': 'lte', 'value': 10})
    assert _matches_rule(15, {'operator': 'gt',  'value': 10})
    assert _matches_rule(10, {'operator': 'gte', 'value': 10})
    assert _matches_rule(10, {'operator': 'eq',  'value': 10})
    assert _matches_rule(5,  {'operator': 'ne',  'value': 10})
    assert not _matches_rule(5, {'operator': 'unknown', 'value': 0})
    assert not _matches_rule('text', {'operator': 'lt', 'value': 0})
