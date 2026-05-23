"""Tests for db_query step capture_rows feature."""
from unittest.mock import MagicMock, patch

import pytest

from flowforge.steps.db_query import DbQueryStep, _render_kv_html, _render_table_html


def make_step(config: dict) -> DbQueryStep:
    return DbQueryStep(name='test_query', config={'on_error': 'stop', **config})


def mock_conn(rows, columns=None):
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute_query.return_value = rows
    conn.execute_query_with_columns.return_value = (rows, columns or [])
    return conn


def run_step(step, conn, context=None):
    with patch.object(step, '_get_connection', return_value=conn):
        return step.run(context or {'steps': {}})


# ── capture_rows = False (default) ────────────────────────────────────────────

def test_no_capture_rows_empty_by_default():
    step = make_step({'query': 'SELECT 1', 'capture_rows': False})
    result = run_step(step, mock_conn([(42,)]))
    assert result.success is True
    assert result.rows == []
    assert result.table_html == ''
    assert result.kv_html == ''


def test_capture_disabled_does_not_call_with_columns():
    step = make_step({'query': 'SELECT 1'})
    conn = mock_conn([(1,)])
    run_step(step, conn)
    conn.execute_query_with_columns.assert_not_called()


# ── capture_rows = True ───────────────────────────────────────────────────────

def test_capture_rows_stores_dicts():
    step = make_step({'query': 'SELECT * FROM t', 'capture_rows': True})
    conn = mock_conn([(10, 'pass'), (5, 'fail')], columns=['count', 'status'])
    result = run_step(step, conn)
    assert result.success is True
    assert result.rows == [{'count': 10, 'status': 'pass'}, {'count': 5, 'status': 'fail'}]


def test_capture_rows_renders_table_html():
    step = make_step({'query': 'SELECT 1', 'capture_rows': True})
    conn = mock_conn([(1, 'ok')], columns=['id', 'status'])
    result = run_step(step, conn)
    assert '<table' in result.table_html
    assert 'id' in result.table_html
    assert 'status' in result.table_html
    assert '>1<' in result.table_html
    assert '>ok<' in result.table_html


def test_capture_rows_renders_kv_html():
    step = make_step({'query': 'SELECT 1', 'capture_rows': True})
    conn = mock_conn([(99,)], columns=['total'])
    result = run_step(step, conn)
    assert '<dl' in result.kv_html
    assert 'total' in result.kv_html
    assert '>99<' in result.kv_html


def test_row_limit_respected():
    step = make_step({'query': 'SELECT 1', 'capture_rows': True, 'row_limit': 2})
    raw = [(i,) for i in range(10)]
    conn = mock_conn(raw, columns=['n'])
    result = run_step(step, conn)
    assert len(result.rows) == 2
    assert result.rows_affected == 10  # full count, not limited


def test_row_limit_default_100():
    step = make_step({'query': 'SELECT 1', 'capture_rows': True})
    raw = [(i,) for i in range(150)]
    conn = mock_conn(raw, columns=['n'])
    result = run_step(step, conn)
    assert len(result.rows) == 100


def test_capture_empty_result():
    step = make_step({'query': 'SELECT 1', 'capture_rows': True})
    conn = mock_conn([], columns=[])
    result = run_step(step, conn)
    assert result.success is True
    assert result.rows == []
    assert result.table_html == ''
    assert result.kv_html == ''


# ── HTML renderer unit tests ──────────────────────────────────────────────────

def test_render_table_html_structure():
    rows = [{'name': 'Alice', 'score': 95}, {'name': 'Bob', 'score': 80}]
    html = _render_table_html(rows)
    assert html.startswith('<table')
    assert '<thead>' in html
    assert '<tbody>' in html
    assert 'Alice' in html
    assert 'Bob' in html
    assert '>score<' in html


def test_render_table_html_escapes_values():
    rows = [{'col': '<script>alert(1)</script>'}]
    html = _render_table_html(rows)
    assert '<script>' not in html
    assert '&lt;script&gt;' in html


def test_render_kv_html_first_row_only():
    rows = [{'a': 1, 'b': 2}, {'a': 99, 'b': 99}]
    html = _render_kv_html(rows)
    assert '>1<' in html
    assert '>99<' not in html


def test_render_kv_html_escapes_values():
    rows = [{'key': '<b>bold</b>'}]
    html = _render_kv_html(rows)
    assert '<b>' not in html
    assert '&lt;b&gt;' in html


def test_render_table_html_empty():
    assert _render_table_html([]) == ''


def test_render_kv_html_empty():
    assert _render_kv_html([]) == ''
