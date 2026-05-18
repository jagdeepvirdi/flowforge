"""Tests for Excel, CSV, and PDF report file generation."""
import csv
import os
import pytest
from pathlib import Path


COLUMNS = ['id', 'name', 'amount', 'date']
ROWS = [
    (1, 'Alice', 1200.50, '2026-01-15'),
    (2, 'Bob',   980.00,  '2026-01-16'),
    (3, 'Carol', 2450.75, '2026-01-17'),
]


# ── CSV ───────────────────────────────────────────────────────────────────────

def test_csv_creates_file(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'report.csv'
    generate(ROWS, COLUMNS, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_csv_header_row(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'report.csv'
    generate(ROWS, COLUMNS, out)
    with open(out, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == COLUMNS


def test_csv_data_rows(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'report.csv'
    generate(ROWS, COLUMNS, out)
    with open(out, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)   # skip header
        data = list(reader)
    assert len(data) == 3
    assert data[0][1] == 'Alice'
    assert data[1][1] == 'Bob'


def test_csv_without_header(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'report.csv'
    generate(ROWS, COLUMNS, out, include_header=False)
    with open(out, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 3
    assert rows[0][1] == 'Alice'


def test_csv_custom_delimiter(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'report.tsv'
    generate(ROWS, COLUMNS, out, delimiter='\t')
    content = out.read_text(encoding='utf-8-sig')
    assert '\t' in content


def test_csv_empty_rows(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'empty.csv'
    generate([], COLUMNS, out)
    with open(out, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        data = list(reader)
    assert header == COLUMNS
    assert data == []


def test_csv_creates_parent_dirs(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'nested' / 'deep' / 'report.csv'
    generate(ROWS, COLUMNS, out)
    assert out.exists()


def test_csv_returns_output_path(tmp_path):
    from flowforge.reports.csv_report import generate
    out = tmp_path / 'report.csv'
    returned = generate(ROWS, COLUMNS, out)
    assert returned == out


# ── Excel ─────────────────────────────────────────────────────────────────────

pytest.importorskip('openpyxl', reason='openpyxl not installed')


def test_excel_creates_file(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'report.xlsx'
    generate(ROWS, COLUMNS, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_excel_header_row(tmp_path):
    from flowforge.reports.excel_report import generate
    from openpyxl import load_workbook
    out = tmp_path / 'report.xlsx'
    generate(ROWS, COLUMNS, out)
    wb = load_workbook(out)
    ws = wb.active
    headers = [ws.cell(1, i + 1).value for i in range(len(COLUMNS))]
    assert headers == COLUMNS


def test_excel_header_is_bold(tmp_path):
    from flowforge.reports.excel_report import generate
    from openpyxl import load_workbook
    out = tmp_path / 'report.xlsx'
    generate(ROWS, COLUMNS, out)
    wb = load_workbook(out)
    ws = wb.active
    assert ws.cell(1, 1).font.bold is True


def test_excel_data_rows(tmp_path):
    from flowforge.reports.excel_report import generate
    from openpyxl import load_workbook
    out = tmp_path / 'report.xlsx'
    generate(ROWS, COLUMNS, out)
    wb = load_workbook(out)
    ws = wb.active
    assert ws.cell(2, 2).value == 'Alice'
    assert ws.cell(3, 2).value == 'Bob'
    assert ws.cell(4, 2).value == 'Carol'


def test_excel_correct_row_count(tmp_path):
    from flowforge.reports.excel_report import generate
    from openpyxl import load_workbook
    out = tmp_path / 'report.xlsx'
    generate(ROWS, COLUMNS, out)
    wb = load_workbook(out)
    ws = wb.active
    assert ws.max_row == len(ROWS) + 1   # header + data rows


def test_excel_custom_sheet_name(tmp_path):
    from flowforge.reports.excel_report import generate
    from openpyxl import load_workbook
    out = tmp_path / 'report.xlsx'
    generate(ROWS, COLUMNS, out, sheet_name='Revenue')
    wb = load_workbook(out)
    assert 'Revenue' in wb.sheetnames


def test_excel_empty_rows(tmp_path):
    from flowforge.reports.excel_report import generate
    from openpyxl import load_workbook
    out = tmp_path / 'empty.xlsx'
    generate([], COLUMNS, out)
    wb = load_workbook(out)
    ws = wb.active
    assert ws.max_row == 1   # header only


def test_excel_creates_parent_dirs(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'nested' / 'report.xlsx'
    generate(ROWS, COLUMNS, out)
    assert out.exists()


def test_excel_returns_output_path(tmp_path):
    from flowforge.reports.excel_report import generate
    out = tmp_path / 'report.xlsx'
    returned = generate(ROWS, COLUMNS, out)
    assert returned == out
