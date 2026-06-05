"""Unit tests for MSSQLConnection and ODBCConnection — pyodbc is fully mocked."""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _make_pyodbc_mock():
    """Return (mock_pyodbc, mock_conn, mock_cursor)."""
    pyodbc = ModuleType('pyodbc')
    pyodbc.SQL_CHAR  = 1
    pyodbc.SQL_WCHAR = 2

    cursor = MagicMock()
    cursor.description = [('col1',), ('col2',)]
    cursor.fetchall.return_value = [(1, 'a'), (2, 'b')]
    cursor.rowcount = 2

    conn = MagicMock()
    conn.cursor.return_value = cursor
    pyodbc.connect = MagicMock(return_value=conn)
    return pyodbc, conn, cursor


# ── MSSQLConnection ────────────────────────────────────────────────────────────

class TestMSSQLConnection:

    def _build(self, pyodbc):
        with patch.dict(sys.modules, {'pyodbc': pyodbc}):
            from flowforge.connections.mssql import MSSQLConnection
            return MSSQLConnection(host='db', database='mydb', user='u', password='p', port=1433)

    def test_import_error_raises(self):
        with patch.dict(sys.modules, {'pyodbc': None}):
            from flowforge.connections.mssql import MSSQLConnection
            with pytest.raises(ImportError, match='pyodbc'):
                MSSQLConnection(host='db', database='mydb', user='u', password='p')

    def test_init_calls_connect(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        self._build(pyodbc)
        pyodbc.connect.assert_called_once()

    def test_init_conn_string_contains_host_and_db(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        self._build(pyodbc)
        conn_str = pyodbc.connect.call_args.args[0]
        assert 'db' in conn_str
        assert 'mydb' in conn_str

    def test_execute_procedure_builds_exec_sql(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        c.execute_procedure('dbo.MyProc', {'p1': 'v1', 'p2': 2})
        sql = cursor.execute.call_args.args[0]
        assert 'EXEC dbo.MyProc' in sql
        assert '@p1=?' in sql
        conn.commit.assert_called()

    def test_execute_procedure_no_params(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        c.execute_procedure('dbo.Proc', {})
        conn.commit.assert_called()

    def test_execute_query_returns_rows(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        rows = c.execute_query('SELECT 1')
        assert rows == [(1, 'a'), (2, 'b')]

    def test_execute_query_with_columns(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        rows, cols = c.execute_query_with_columns('SELECT *')
        assert cols == ['col1', 'col2']
        assert len(rows) == 2

    def test_execute_query_with_columns_no_description(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        cursor.description = None
        c = self._build(pyodbc)
        c._conn = conn
        _, cols = c.execute_query_with_columns('SELECT 1')
        assert cols == []

    def test_execute_write_commits(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        count = c.execute_write("DELETE FROM t WHERE id=?", (1,))
        assert count == 2
        conn.commit.assert_called()

    def test_execute_many_sets_fast_executemany(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        count = c.execute_many("INSERT INTO t VALUES (?)", [(1,), (2,)])
        assert cursor.fast_executemany is True
        assert count == 2
        conn.commit.assert_called()

    def test_make_placeholders(self):
        pyodbc, _, _ = _make_pyodbc_mock()
        c = self._build(pyodbc)
        assert c.make_placeholders(3) == '?, ?, ?'
        assert c.make_placeholders(1) == '?'

    def test_test_success(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        ok, ms = c.test()
        assert ok is True
        assert ms >= 0

    def test_test_failure(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        cursor.execute.side_effect = Exception('connection refused')
        c = self._build(pyodbc)
        c._conn = conn
        ok, ms = c.test()
        assert ok is False
        assert ms == 0

    def test_close_calls_conn_close(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        c = self._build(pyodbc)
        c._conn = conn
        c.close()
        conn.close.assert_called_once()

    def test_close_swallows_exception(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        conn.close.side_effect = Exception('already closed')
        c = self._build(pyodbc)
        c._conn = conn
        c.close()  # must not raise


# ── ODBCConnection ─────────────────────────────────────────────────────────────

class TestODBCConnection:

    def _build_dsn(self, pyodbc):
        with patch.dict(sys.modules, {'pyodbc': pyodbc}):
            from flowforge.connections.odbc import ODBCConnection
            return ODBCConnection(dsn='myDSN')

    def _build_conn_str(self, pyodbc):
        with patch.dict(sys.modules, {'pyodbc': pyodbc}):
            from flowforge.connections.odbc import ODBCConnection
            return ODBCConnection(connection_string='Driver={SQL};Server=x;Database=y;')

    def test_import_error_raises(self):
        with patch.dict(sys.modules, {'pyodbc': None}):
            from flowforge.connections.odbc import ODBCConnection
            with pytest.raises(ImportError, match='pyodbc'):
                ODBCConnection(dsn='x')

    def test_no_dsn_or_conn_str_raises(self):
        pyodbc, _, _ = _make_pyodbc_mock()
        with patch.dict(sys.modules, {'pyodbc': pyodbc}):
            from flowforge.connections.odbc import ODBCConnection
            with pytest.raises(ValueError):
                ODBCConnection()

    def test_init_with_dsn_uses_dsn_prefix(self):
        pyodbc, _, _ = _make_pyodbc_mock()
        self._build_dsn(pyodbc)
        conn_str = pyodbc.connect.call_args.args[0]
        assert 'DSN=myDSN' in conn_str

    def test_init_with_connection_string(self):
        pyodbc, _, _ = _make_pyodbc_mock()
        self._build_conn_str(pyodbc)
        pyodbc.connect.assert_called_once()

    def test_execute_procedure_uses_call_syntax(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        c.execute_procedure('MyProc', {'a': 1, 'b': 2})
        sql = cursor.execute.call_args.args[0]
        assert '{CALL MyProc' in sql
        conn.commit.assert_called()

    def test_execute_procedure_no_params(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        c.execute_procedure('MyProc', {})
        conn.commit.assert_called()

    def test_execute_query_returns_rows(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        rows = c.execute_query('SELECT 1')
        assert rows == [(1, 'a'), (2, 'b')]

    def test_execute_query_with_columns(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        rows, cols = c.execute_query_with_columns('SELECT *')
        assert cols == ['col1', 'col2']
        assert len(rows) == 2

    def test_execute_query_with_columns_no_description(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        cursor.description = None
        c = self._build_dsn(pyodbc)
        c._conn = conn
        _, cols = c.execute_query_with_columns('SELECT *')
        assert cols == []

    def test_execute_write_commits(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        count = c.execute_write("UPDATE t SET x=? WHERE id=?", (1, 2))
        assert count == 2
        conn.commit.assert_called()

    def test_execute_many(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        count = c.execute_many("INSERT INTO t VALUES (?)", [(1,), (2,)])
        assert count == 2
        conn.commit.assert_called()

    def test_make_placeholders(self):
        pyodbc, _, _ = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        assert c.make_placeholders(3) == '?, ?, ?'
        assert c.make_placeholders(0) == ''

    def test_test_success(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        ok, ms = c.test()
        assert ok is True
        assert ms >= 0

    def test_test_failure(self):
        pyodbc, conn, cursor = _make_pyodbc_mock()
        cursor.execute.side_effect = Exception('driver error')
        c = self._build_dsn(pyodbc)
        c._conn = conn
        ok, ms = c.test()
        assert ok is False
        assert ms == 0

    def test_close_calls_conn_close(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        c = self._build_dsn(pyodbc)
        c._conn = conn
        c.close()
        conn.close.assert_called_once()

    def test_close_swallows_exception(self):
        pyodbc, conn, _ = _make_pyodbc_mock()
        conn.close.side_effect = Exception('fail')
        c = self._build_dsn(pyodbc)
        c._conn = conn
        c.close()  # must not raise
