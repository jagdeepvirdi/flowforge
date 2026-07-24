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


def test_pool_created_with_connect_timeout():
    """Without a connect_timeout, opening a pool against a dead host hangs for
    the OS-level TCP timeout (minutes) instead of failing fast."""
    with patch('psycopg2.pool.ThreadedConnectionPool', return_value=MagicMock()) as mock_pool_cls:
        from flowforge.connections.postgres import PostgreSQLConnection
        PostgreSQLConnection(host='h', database='d', user='u', password='p')

    _, kwargs = mock_pool_cls.call_args
    assert kwargs.get('connect_timeout') == 5


class TestPostgreSQLChunkedStreaming:
    """execute_query_with_columns_chunked uses a named (server-side) cursor.

    Its description is only populated after the first fetch (a real psycopg2
    quirk, confirmed against a live Postgres) — these tests pin that behavior
    with a mock cursor whose `.description` mimics it exactly.
    """

    def _build_streaming(self, rows, description_before=None, description_after=None):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        remaining = list(rows)

        def fake_fetchone():
            mock_cursor.description = description_after
            return remaining.pop(0) if remaining else None

        mock_cursor.description = description_before
        mock_cursor.fetchone.side_effect = fake_fetchone
        mock_cursor.__iter__ = lambda self: iter(remaining)
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn

        with patch('psycopg2.pool.ThreadedConnectionPool', return_value=mock_pool):
            from flowforge.connections.postgres import PostgreSQLConnection
            c = PostgreSQLConnection(host='h', database='d', user='u', password='p')

        return c, mock_conn, mock_cursor

    def test_uses_named_cursor_with_itersize(self):
        c, mock_conn, _ = self._build_streaming(
            [(1, 'a')], description_after=[('id',), ('name',)],
        )
        c.execute_query_with_columns_chunked('SELECT 1', chunk_size=250)
        _, kwargs = mock_conn.cursor.call_args
        assert 'name' in kwargs and kwargs['name']
        assert mock_conn.cursor.return_value.itersize == 250

    def test_columns_available_despite_none_description_before_fetch(self):
        """Regression test: description is None right after execute() on a
        named cursor — reading it before the peek fetchone() would silently
        return an empty column list."""
        c, _, _ = self._build_streaming(
            [(1, 'a'), (2, 'b')],
            description_before=None,
            description_after=[('id',), ('name',)],
        )
        columns, row_iter = c.execute_query_with_columns_chunked('SELECT 1')
        assert columns == ['id', 'name']
        assert list(row_iter) == [(1, 'a'), (2, 'b')]

    def test_zero_rows_still_returns_columns(self):
        c, _, _ = self._build_streaming(
            [], description_before=None, description_after=[('id',)],
        )
        columns, row_iter = c.execute_query_with_columns_chunked('SELECT 1 WHERE 1=0')
        assert columns == ['id']
        assert list(row_iter) == []

    def test_cursor_closed_after_streaming(self):
        c, _, mock_cursor = self._build_streaming(
            [(1,)], description_after=[('id',)],
        )
        _, row_iter = c.execute_query_with_columns_chunked('SELECT 1')
        list(row_iter)  # fully drain
        mock_cursor.close.assert_called_once()


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
