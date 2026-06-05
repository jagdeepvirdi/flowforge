"""Extended unit tests for MySQLConnection — covers execute_procedure and
execute_query_with_columns (previously uncovered lines 46-49, 57-60).

Builds on the patching approach already used in test_mysql.py.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clear_mysql_pools():
    import flowforge.connections.mysql as m
    m._pools.clear()
    yield
    m._pools.clear()


@pytest.fixture()
def pymysql_mock():
    fake = MagicMock()
    fake_conn = MagicMock()
    fake_cursor = MagicMock()
    fake_cursor.description = [('id',), ('name',)]
    fake_cursor.fetchall.return_value = [(1, 'Alice'), (2, 'Bob')]
    fake_cursor.rowcount = 2
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cursor)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    fake.connect.return_value = fake_conn
    fake.cursors = MagicMock()
    fake.cursors.Cursor = MagicMock()
    mods = {'pymysql': fake, 'pymysql.connections': MagicMock(), 'pymysql.cursors': MagicMock()}
    with patch.dict(sys.modules, mods):
        yield fake, fake_conn, fake_cursor


def _build(pymysql_mock):
    fake, fake_conn, fake_cursor = pymysql_mock
    from flowforge.connections.mysql import MySQLConnection
    conn = MySQLConnection(host='db', database='mydb', user='u', password='p')
    conn._conn = fake_conn
    return conn, fake_conn, fake_cursor


class TestMySQLExecuteProcedure:

    def test_calls_callproc(self, pymysql_mock):
        conn, fake_conn, fake_cursor = _build(pymysql_mock)
        conn.execute_procedure('sp_monthly', {'p_month': '2026-05', 'p_run': 42})
        fake_cursor.callproc.assert_called_once_with('sp_monthly', ['2026-05', 42])
        fake_conn.commit.assert_called_once()

    def test_empty_params(self, pymysql_mock):
        conn, fake_conn, fake_cursor = _build(pymysql_mock)
        conn.execute_procedure('sp_no_args', {})
        fake_cursor.callproc.assert_called_once_with('sp_no_args', [])
        fake_conn.commit.assert_called_once()


class TestMySQLExecuteQueryWithColumns:

    def test_returns_rows_and_column_names(self, pymysql_mock):
        conn, _, _ = _build(pymysql_mock)
        rows, cols = conn.execute_query_with_columns('SELECT id, name FROM t')
        assert cols == ['id', 'name']
        assert rows == [(1, 'Alice'), (2, 'Bob')]

    def test_no_description_returns_empty_cols(self, pymysql_mock):
        fake, fake_conn, fake_cursor = pymysql_mock
        fake_cursor.description = None
        conn, _, _ = _build(pymysql_mock)
        rows, cols = conn.execute_query_with_columns('SELECT 1')
        assert cols == []

    def test_passes_params(self, pymysql_mock):
        conn, _, fake_cursor = _build(pymysql_mock)
        conn.execute_query_with_columns('SELECT * FROM t WHERE id=%s', (5,))
        fake_cursor.execute.assert_called_once_with('SELECT * FROM t WHERE id=%s', (5,))
