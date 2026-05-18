"""Tests for DbQueryStep and DbProcedureStep using mocked connections."""
import pytest
from unittest.mock import MagicMock, patch, call
from flowforge.steps.base import StepResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_conn(rows=None, side_effect=None):
    """Return a mock connection that behaves like BaseConnection."""
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    if side_effect:
        conn.execute_query.side_effect = side_effect
    else:
        conn.execute_query.return_value = rows or []
    conn.execute_write.return_value = 0
    conn.execute_procedure.return_value = None
    return conn


def run_query_step(config, context=None, mock_conn=None):
    from flowforge.steps.db_query import DbQueryStep
    if mock_conn is None:
        mock_conn = make_mock_conn()
    step = DbQueryStep('query', config)
    with patch.object(step, '_get_connection', return_value=mock_conn):
        return step.run(context or {})


def run_procedure_step(config, context=None, mock_conn=None):
    from flowforge.steps.db_procedure import DbProcedureStep
    if mock_conn is None:
        mock_conn = make_mock_conn()
    step = DbProcedureStep('proc', config)
    with patch.object(step, '_get_connection', return_value=mock_conn):
        return step.run(context or {})


# ── DbQueryStep — basic execution ─────────────────────────────────────────────

def test_query_step_success():
    rows = [(1, 'Alice'), (2, 'Bob')]
    conn = make_mock_conn(rows=rows)
    result = run_query_step({'query': 'SELECT id, name FROM users'}, mock_conn=conn)
    assert result.success is True
    assert result.rows_affected == 2


def test_query_step_calls_execute_query():
    conn = make_mock_conn(rows=[])
    run_query_step({'query': 'SELECT 1'}, mock_conn=conn)
    conn.execute_query.assert_called_once_with('SELECT 1')


def test_query_step_empty_result():
    conn = make_mock_conn(rows=[])
    result = run_query_step({'query': 'SELECT * FROM empty_table'}, mock_conn=conn)
    assert result.success is True
    assert result.rows_affected == 0


def test_query_step_db_error_returns_failure():
    conn = make_mock_conn(side_effect=Exception('relation does not exist'))
    result = run_query_step({'query': 'SELECT * FROM missing'}, mock_conn=conn)
    assert result.success is False
    assert 'relation does not exist' in result.error


# ── DbQueryStep — output table ─────────────────────────────────────────────────

def test_query_step_writes_to_output_table():
    rows = [(1, 'x'), (2, 'y')]
    conn = make_mock_conn(rows=rows)
    run_query_step(
        {'query': 'SELECT id, v FROM src', 'output_table': 'staging.out', 'mode': 'replace'},
        mock_conn=conn,
    )
    conn.execute_write.assert_called()
    write_calls = conn.execute_write.call_args_list
    sqls = [c[0][0] for c in write_calls]
    assert any('TRUNCATE' in s for s in sqls)
    assert any('INSERT INTO staging.out' in s for s in sqls)


def test_query_step_append_mode_no_truncate():
    rows = [(1,)]
    conn = make_mock_conn(rows=rows)
    run_query_step(
        {'query': 'SELECT 1', 'output_table': 'staging.out', 'mode': 'append'},
        mock_conn=conn,
    )
    write_calls = conn.execute_write.call_args_list
    sqls = [c[0][0] for c in write_calls]
    assert not any('TRUNCATE' in s for s in sqls)
    assert any('INSERT' in s for s in sqls)


def test_query_step_invalid_mode_returns_failure():
    result = run_query_step(
        {'query': 'SELECT 1', 'output_table': 'out', 'mode': 'overwrite'}
    )
    assert result.success is False
    assert 'Invalid mode' in result.error


def test_query_step_no_output_table_no_write():
    rows = [(1,), (2,)]
    conn = make_mock_conn(rows=rows)
    run_query_step({'query': 'SELECT 1'}, mock_conn=conn)
    conn.execute_write.assert_not_called()


# ── DbQueryStep — Jinja2 variable resolution ──────────────────────────────────

def test_query_step_resolves_context_variables():
    conn = make_mock_conn(rows=[])
    run_query_step(
        {'query': "SELECT * FROM sales WHERE period = '{{ current_month }}'"},
        context={'current_month': '2026-05'},
        mock_conn=conn,
    )
    actual_sql = conn.execute_query.call_args[0][0]
    assert '2026-05' in actual_sql
    assert '{{' not in actual_sql


# ── DbProcedureStep ────────────────────────────────────────────────────────────

def test_procedure_step_success():
    conn = make_mock_conn()
    result = run_procedure_step(
        {'procedure': 'pkg_revenue.populate', 'params': {}},
        mock_conn=conn,
    )
    assert result.success is True


def test_procedure_step_calls_execute_procedure():
    conn = make_mock_conn()
    run_procedure_step(
        {'procedure': 'my_proc', 'params': {'p1': 'val1', 'p2': 'val2'}},
        mock_conn=conn,
    )
    conn.execute_procedure.assert_called_once_with('my_proc', {'p1': 'val1', 'p2': 'val2'})


def test_procedure_step_no_params():
    conn = make_mock_conn()
    result = run_procedure_step({'procedure': 'refresh_cache'}, mock_conn=conn)
    assert result.success is True
    conn.execute_procedure.assert_called_once_with('refresh_cache', {})


def test_procedure_step_resolves_param_variables():
    conn = make_mock_conn()
    run_procedure_step(
        {'procedure': 'load_month', 'params': {'period': '{{ current_month }}'}},
        context={'current_month': '2026-04'},
        mock_conn=conn,
    )
    _, kwargs_or_args = conn.execute_procedure.call_args
    # call_args is (args, kwargs); params is second positional arg
    called_params = conn.execute_procedure.call_args[0][1]
    assert called_params['period'] == '2026-04'


def test_procedure_step_db_error_returns_failure():
    conn = make_mock_conn()
    conn.execute_procedure.side_effect = Exception('ORA-00900: invalid SQL')
    result = run_procedure_step(
        {'procedure': 'bad_proc', 'params': {}},
        mock_conn=conn,
    )
    assert result.success is False
    assert 'ORA-00900' in result.error


def test_procedure_step_logs_field_set():
    conn = make_mock_conn()
    result = run_procedure_step(
        {'procedure': 'do_something', 'params': {'a': '1', 'b': '2'}},
        mock_conn=conn,
    )
    assert result.logs is not None
    assert 'do_something' in result.logs


# ── PostgreSQLConnection unit tests (mocked psycopg2) ─────────────────────────

def test_postgres_execute_query_returns_rows():
    from flowforge.connections.postgres import PostgreSQLConnection

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchall.return_value = [(1,), (2,)]
    mock_conn.cursor.return_value = mock_cursor

    with patch('psycopg2.pool.ThreadedConnectionPool') as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_pool_cls.return_value = mock_pool

        conn = PostgreSQLConnection('localhost', 'testdb', 'user', 'pass')
        rows = conn.execute_query('SELECT 1')

    assert rows == [(1,), (2,)]


def test_postgres_test_returns_true_on_success():
    from flowforge.connections.postgres import PostgreSQLConnection

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchall.return_value = [(1,)]
    mock_conn.cursor.return_value = mock_cursor

    with patch('psycopg2.pool.ThreadedConnectionPool') as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_pool_cls.return_value = mock_pool

        pg = PostgreSQLConnection('localhost', 'testdb', 'user', 'pass', port=5434)
        ok, latency = pg.test()

    assert ok is True
    assert latency >= 0
