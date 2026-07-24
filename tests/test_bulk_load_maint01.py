"""Regression tests for MAINT-01: flowforge/steps/bulk_load.py's raw-connection
and INSERT-placeholder paths used to hand-roll their own postgresql/oracle-only
driver dispatch and hardcode '%s' placeholders. Both now delegate to the same
flowforge.connections.factory registry used everywhere else in the app.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _oracle_conn_cfg(**kw) -> dict:
    cfg = {'_db_type': 'oracle', 'username': 'usr', 'password': 'pwd',
           'host': 'dbhost', 'port': 1521, 'service_name': 'ORCL'}
    cfg.update(kw)
    return cfg


def _mssql_conn_cfg(**kw) -> dict:
    cfg = {'_db_type': 'mssql', 'username': 'sa', 'password': 'pwd',
           'host': 'sqlhost', 'port': 1433, 'database': 'mydb'}
    cfg.update(kw)
    return cfg


# ─── _make_placeholders — per-db_type placeholder syntax ─────────────────────

@pytest.mark.parametrize(('db_type', 'expected'), [
    ('postgresql', '%s, %s, %s'),
    ('mysql', '%s, %s, %s'),
    ('snowflake', '%s, %s, %s'),
    ('oracle', ':1, :2, :3'),
    ('mssql', '?, ?, ?'),
    ('odbc', '?, ?, ?'),
])
def test_make_placeholders_matches_db_type(db_type, expected):
    from flowforge.steps.bulk_load import _make_placeholders
    assert _make_placeholders({'_db_type': db_type}, 3) == expected


def test_make_placeholders_unsupported_db_type_raises():
    from flowforge.steps.bulk_load import _make_placeholders
    with pytest.raises(ValueError, match='Unsupported db_type'):
        _make_placeholders({'_db_type': 'mongodb'}, 2)


# ─── The actual bug: python fallback built invalid SQL for non-Postgres DBs ───

def test_python_fallback_uses_oracle_placeholders_not_percent_s(tmp_path):
    """Before MAINT-01, this hardcoded '%s' — invalid bind-variable syntax for
    oracledb, which uses ':1', ':2', etc. The INSERT would have failed against
    a real Oracle connection with a syntax/bind error on every load."""
    from flowforge.steps.bulk_load import _load_python_fallback

    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')

    conn = MagicMock()
    cur = MagicMock()
    cur.rowcount = 1
    conn.cursor.return_value = cur

    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _load_python_fallback(
            _oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', []
        )

    insert_sql = cur.executemany.call_args[0][0]
    assert ':1, :2' in insert_sql
    assert '%s' not in insert_sql


def test_dry_run_insert_rows_uses_mssql_placeholders(tmp_path):
    from flowforge.steps.bulk_load import _dry_run_insert_rows

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur

    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _dry_run_insert_rows(_mssql_conn_cfg(), 'tbl', ['id', 'name'], [['1', 'Alice']])

    # First cur.execute call after the SAVEPOINT is the INSERT itself.
    insert_calls = [c for c in cur.execute.call_args_list if 'INSERT' in c[0][0]]
    assert insert_calls, cur.execute.call_args_list
    assert '?, ?' in insert_calls[0][0][0]


# ─── _open_raw_connection — extended db_type coverage ─────────────────────────

def test_open_raw_conn_mysql_delegates_to_factory():
    """MySQL isn't pooled (flowforge/connections/mysql.py opens a fresh
    connection per instantiation), so delegating to build_connection() here is
    a pure extension, not a pooling-behavior change."""
    from flowforge.steps.bulk_load import _open_raw_connection

    fake_pymysql = MagicMock()
    fake_conn = MagicMock()
    fake_pymysql.connect.return_value = fake_conn
    modules = {
        'pymysql': fake_pymysql,
        'pymysql.connections': MagicMock(),
        'pymysql.cursors': MagicMock(),
    }
    conn_cfg = {'_db_type': 'mysql', 'username': 'u', 'password': 'p',
                'host': 'myhost', 'port': 3306, 'database': 'mydb'}
    with patch.dict(sys.modules, modules):
        result = _open_raw_connection(conn_cfg)

    assert result is fake_conn
    fake_pymysql.connect.assert_called_once()
    kwargs = fake_pymysql.connect.call_args.kwargs
    assert kwargs['host'] == 'myhost'
    assert kwargs['database'] == 'mydb'
    assert kwargs['user'] == 'u'


def test_open_raw_conn_mssql_delegates_to_factory():
    from flowforge.steps.bulk_load import _open_raw_connection

    fake_pyodbc = MagicMock()
    fake_conn = MagicMock()
    fake_pyodbc.connect.return_value = fake_conn
    with patch.dict(sys.modules, {'pyodbc': fake_pyodbc}):
        result = _open_raw_connection(_mssql_conn_cfg())

    assert result is fake_conn
    conn_str = fake_pyodbc.connect.call_args.args[0]
    assert 'SERVER=sqlhost,1433' in conn_str
    assert 'DATABASE=mydb' in conn_str


def test_open_raw_conn_odbc_delegates_to_factory():
    from flowforge.steps.bulk_load import _open_raw_connection

    fake_pyodbc = MagicMock()
    fake_conn = MagicMock()
    fake_pyodbc.connect.return_value = fake_conn
    conn_cfg = {'_db_type': 'odbc', 'dsn': 'MyDSN', 'connection_string': ''}
    with patch.dict(sys.modules, {'pyodbc': fake_pyodbc}):
        result = _open_raw_connection(conn_cfg)

    assert result is fake_conn
    fake_pyodbc.connect.assert_called_once_with('DSN=MyDSN', autocommit=False, timeout=10)


def test_open_raw_conn_snowflake_delegates_to_factory():
    from flowforge.steps.bulk_load import _open_raw_connection

    fake_conn = MagicMock()
    connector = ModuleType('snowflake.connector')
    connector.connect = MagicMock(return_value=fake_conn)
    snowflake_pkg = ModuleType('snowflake')
    snowflake_pkg.connector = connector

    conn_cfg = {
        '_db_type': 'snowflake', 'account': 'acct', 'username': 'u', 'password': 'p',
        'warehouse': 'WH', 'database': 'DB', 'schema': 'PUBLIC', 'role': '',
    }
    with patch.dict(sys.modules, {'snowflake': snowflake_pkg, 'snowflake.connector': connector}):
        result = _open_raw_connection(conn_cfg)

    assert result is fake_conn
    connector.connect.assert_called_once()


def test_open_raw_conn_bigquery_still_unsupported():
    """BigQuery isn't in _NON_POOLED_DB_TYPES (no raw DB-API connection to
    expose — see BaseConnection.raw_connection) and was never supported by
    bulk_load's raw-connection path — this must keep raising, not regress into
    an unhandled NotImplementedError from deep inside the factory."""
    from flowforge.steps.bulk_load import _open_raw_connection
    with pytest.raises(ValueError, match='Unsupported db_type for bulk_load'):
        _open_raw_connection({'_db_type': 'bigquery'})


def test_open_raw_conn_postgres_and_oracle_unchanged():
    """postgresql/oracle must keep opening a direct, non-pooled connection —
    not delegate to build_connection(), which would route them through
    flowforge.connections.postgres/oracle's connection pools instead."""
    from flowforge.steps.bulk_load import _NON_POOLED_DB_TYPES
    assert 'postgresql' not in _NON_POOLED_DB_TYPES
    assert 'oracle' not in _NON_POOLED_DB_TYPES
