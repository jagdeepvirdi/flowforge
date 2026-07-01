"""Unit tests for flowforge/connections/snowflake.py — mocks snowflake.connector."""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch


def _make_snowflake_mock():
    cursor = MagicMock()
    cursor.description = [('col1',), ('col2',)]
    cursor.fetchall.return_value = [(1, 'a'), (2, 'b')]
    cursor.rowcount = 2
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cursor

    connector = ModuleType('snowflake.connector')
    connector.connect = MagicMock(return_value=conn)

    snowflake_pkg = ModuleType('snowflake')
    snowflake_pkg.connector = connector

    return snowflake_pkg, connector, conn, cursor


def _build(snowflake_pkg, connector, **kwargs):
    with patch.dict(sys.modules, {'snowflake': snowflake_pkg, 'snowflake.connector': connector}):
        from flowforge.connections.snowflake import SnowflakeConnection
        return SnowflakeConnection(
            account=kwargs.get('account', 'myaccount'),
            user=kwargs.get('user', 'u'),
            password=kwargs.get('password', 'p'),
            warehouse=kwargs.get('warehouse', 'WH'),
            database=kwargs.get('database', 'DB'),
            schema=kwargs.get('schema', 'PUBLIC'),
            role=kwargs.get('role', ''),
        )


def test_import_error_when_driver_missing():
    with patch.dict(sys.modules, {'snowflake.connector': None}):
        from flowforge.connections.snowflake import SnowflakeConnection
        try:
            SnowflakeConnection(account='a', user='u', password='p')
            raise AssertionError("expected ImportError")
        except ImportError as e:
            assert 'snowflake-connector-python' in str(e)


def test_db_type():
    from flowforge.connections.snowflake import SnowflakeConnection
    assert SnowflakeConnection.db_type == 'snowflake'


def test_connect_passes_account_and_credentials():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    _build(snowflake_pkg, connector, account='myaccount', user='alice', password='secret')
    _, kwargs = connector.connect.call_args
    assert kwargs['account'] == 'myaccount'
    assert kwargs['user'] == 'alice'
    assert kwargs['password'] == 'secret'


def test_optional_fields_become_none_when_blank():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    with patch.dict(sys.modules, {'snowflake': snowflake_pkg, 'snowflake.connector': connector}):
        from flowforge.connections.snowflake import SnowflakeConnection
        SnowflakeConnection(account='a', user='u', password='p')
    _, kwargs = connector.connect.call_args
    assert kwargs['warehouse'] is None
    assert kwargs['database'] is None
    assert kwargs['schema'] is None
    assert kwargs['role'] is None


def test_execute_query_returns_rows():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    rows = conn_obj.execute_query("SELECT * FROM t")
    assert rows == [(1, 'a'), (2, 'b')]


def test_execute_query_with_columns():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    rows, columns = conn_obj.execute_query_with_columns("SELECT * FROM t")
    assert columns == ['col1', 'col2']
    assert rows == [(1, 'a'), (2, 'b')]


def test_execute_write_commits_and_returns_rowcount():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    rows = conn_obj.execute_write("UPDATE t SET x=1")
    assert rows == 2
    conn.commit.assert_called()


def test_execute_procedure_builds_call_statement():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    conn_obj.execute_procedure('my_proc', {'a': 1, 'b': 2})
    sql = cursor.execute.call_args[0][0]
    assert sql == 'CALL my_proc(%s, %s)'


def test_make_placeholders():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    assert conn_obj.make_placeholders(3) == '%s, %s, %s'


def test_test_success():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    ok, latency = conn_obj.test()
    assert ok is True
    assert latency >= 0


def test_test_failure_returns_false():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    cursor.execute.side_effect = Exception('boom')
    ok, latency = conn_obj.test()
    assert ok is False
    assert latency == 0


def test_close_swallows_exceptions():
    snowflake_pkg, connector, conn, cursor = _make_snowflake_mock()
    conn_obj = _build(snowflake_pkg, connector)
    conn.close.side_effect = Exception('already closed')
    conn_obj.close()  # must not raise
