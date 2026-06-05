"""Unit tests for PostgreSQLConnection — covers the methods not hit by integration
tests: execute_procedure, execute_write, execute_many, make_placeholders, and
the test() failure path (lines 31-36, 50-54, 57-61, 64, 71-73 of postgres.py).
"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clear_pg_pools():
    import flowforge.connections.postgres as pg
    pg._pools.clear()
    yield
    pg._pools.clear()


def _build():
    """Return a PostgreSQLConnection backed by mocked psycopg2 pool."""
    mock_pool  = MagicMock()
    mock_conn  = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.description = [('col1',), ('col2',)]
    mock_cursor.fetchall.return_value = [(1, 'a'), (2, 'b')]
    mock_cursor.rowcount = 3

    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_pool.getconn.return_value = mock_conn

    with patch('psycopg2.pool.ThreadedConnectionPool', return_value=mock_pool):
        from flowforge.connections.postgres import PostgreSQLConnection
        c = PostgreSQLConnection(host='h', database='d', user='u', password='p')

    return c, mock_conn, mock_cursor


class TestPostgreSQLExecuteProcedure:

    def test_builds_call_sql(self):
        c, mock_conn, mock_cursor = _build()
        c.execute_procedure('pkg.populate_report', {'p_month': '2026-05', 'p_id': 1})
        sql = mock_cursor.execute.call_args.args[0]
        assert 'CALL pkg.populate_report' in sql
        assert '%s' in sql
        mock_conn.commit.assert_called_once()

    def test_no_params(self):
        c, mock_conn, mock_cursor = _build()
        c.execute_procedure('noop_proc', {})
        mock_conn.commit.assert_called_once()


class TestPostgreSQLExecuteWrite:

    def test_returns_row_count(self):
        c, mock_conn, mock_cursor = _build()
        count = c.execute_write('DELETE FROM t WHERE id = %s', (42,))
        assert count == 3
        mock_conn.commit.assert_called_once()

    def test_no_params(self):
        c, mock_conn, mock_cursor = _build()
        c.execute_write('TRUNCATE t')
        mock_conn.commit.assert_called_once()


class TestPostgreSQLExecuteMany:

    def test_returns_row_count(self):
        c, mock_conn, mock_cursor = _build()
        rows = [(1, 'x'), (2, 'y')]
        with patch('psycopg2.extras.execute_batch'):
            result = c.execute_many('INSERT INTO t VALUES (%s,%s)', rows)
        assert result == 2
        mock_conn.commit.assert_called_once()

    def test_uses_execute_batch(self):
        c, mock_conn, mock_cursor = _build()
        with patch('psycopg2.extras.execute_batch') as mock_batch:
            c.execute_many('INSERT INTO t VALUES (%s)', [(1,), (2,), (3,)])
        mock_batch.assert_called_once()
        mock_conn.commit.assert_called_once()


class TestPostgreSQLMakePlaceholders:

    def test_single(self):
        c, _, _ = _build()
        assert c.make_placeholders(1) == '%s'

    def test_multiple(self):
        c, _, _ = _build()
        assert c.make_placeholders(4) == '%s, %s, %s, %s'

    def test_zero(self):
        c, _, _ = _build()
        assert c.make_placeholders(0) == ''


class TestPostgreSQLTest:

    def test_failure_returns_false(self):
        c, mock_conn, mock_cursor = _build()
        mock_cursor.execute.side_effect = Exception('connection reset')
        ok, ms = c.test()
        assert ok is False
        assert ms == 0
