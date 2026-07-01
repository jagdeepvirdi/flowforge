"""Unit tests for connections/factory.get_connection."""
from unittest.mock import MagicMock, patch

import pytest


def _make_row(db_type: str):
    row = MagicMock()
    row.db_type = db_type
    row.config = {}
    return row


def _db_patch(row):
    mock_db = MagicMock()
    mock_db.session.get.return_value = row
    return patch('flowforge.db.models.db', mock_db)


def test_not_found_raises():
    mock_db = MagicMock()
    mock_db.session.get.return_value = None
    with patch('flowforge.db.models.db', mock_db):
        with pytest.raises(ValueError, match='not found'):
            from flowforge.connections.factory import get_connection
            get_connection('missing-id')


def test_postgresql_connection_returned():
    cfg = {'host': 'localhost', 'database': 'db', 'user': 'u', 'password': 'p', 'port': 5432}
    row = _make_row('postgresql')
    with _db_patch(row), \
         patch('flowforge.crypto.decrypt_config', return_value=cfg), \
         patch('flowforge.connections.postgres.PostgreSQLConnection.__init__', return_value=None):
        from flowforge.connections.factory import get_connection
        from flowforge.connections.postgres import PostgreSQLConnection
        conn = get_connection('pg-id')
        assert isinstance(conn, PostgreSQLConnection)


def test_mysql_connection_returned():
    cfg = {'host': 'localhost', 'database': 'db', 'user': 'u', 'password': 'p', 'port': 3306}
    row = _make_row('mysql')
    with _db_patch(row), \
         patch('flowforge.crypto.decrypt_config', return_value=cfg), \
         patch('flowforge.connections.mysql.MySQLConnection.__init__', return_value=None):
        from flowforge.connections.factory import get_connection
        from flowforge.connections.mysql import MySQLConnection
        conn = get_connection('mysql-id')
        assert isinstance(conn, MySQLConnection)


def test_oracle_connection_returned():
    cfg = {'host': 'ora-host', 'port': 1521, 'service_name': 'ORCL', 'user': 'u', 'password': 'p'}
    row = _make_row('oracle')
    with _db_patch(row), \
         patch('flowforge.crypto.decrypt_config', return_value=cfg), \
         patch('flowforge.connections.oracle.OracleConnection.__init__', return_value=None):
        from flowforge.connections.factory import get_connection
        from flowforge.connections.oracle import OracleConnection
        conn = get_connection('oracle-id')
        assert isinstance(conn, OracleConnection)


def test_redshift_connection_returned():
    cfg = {'host': 'redshift-cluster.example.com', 'database': 'dev', 'user': 'u', 'password': 'p', 'port': 5439}
    row = _make_row('redshift')
    with _db_patch(row), \
         patch('flowforge.crypto.decrypt_config', return_value=cfg), \
         patch('flowforge.connections.redshift.RedshiftConnection.__init__', return_value=None):
        from flowforge.connections.factory import get_connection
        from flowforge.connections.redshift import RedshiftConnection
        conn = get_connection('redshift-id')
        assert isinstance(conn, RedshiftConnection)


def test_snowflake_connection_returned():
    cfg = {'account': 'acct', 'user': 'u', 'password': 'p', 'warehouse': 'WH', 'database': 'DB', 'schema': 'PUBLIC', 'role': ''}
    row = _make_row('snowflake')
    with _db_patch(row), \
         patch('flowforge.crypto.decrypt_config', return_value=cfg), \
         patch('flowforge.connections.snowflake.SnowflakeConnection.__init__', return_value=None):
        from flowforge.connections.factory import get_connection
        from flowforge.connections.snowflake import SnowflakeConnection
        conn = get_connection('snowflake-id')
        assert isinstance(conn, SnowflakeConnection)


def test_bigquery_connection_returned():
    cfg = {'project_id': 'my-project', 'dataset': 'my_dataset', 'credentials_json': ''}
    row = _make_row('bigquery')
    with _db_patch(row), \
         patch('flowforge.crypto.decrypt_config', return_value=cfg), \
         patch('flowforge.connections.bigquery.BigQueryConnection.__init__', return_value=None):
        from flowforge.connections.bigquery import BigQueryConnection
        from flowforge.connections.factory import get_connection
        conn = get_connection('bigquery-id')
        assert isinstance(conn, BigQueryConnection)


def test_unsupported_type_raises():
    row = _make_row('mongodb')
    cfg = {'host': 'x', 'database': 'y', 'user': 'u', 'password': 'p'}
    with _db_patch(row), patch('flowforge.crypto.decrypt_config', return_value=cfg):
        with pytest.raises(ValueError, match='Unsupported db_type'):
            from flowforge.connections.factory import get_connection
            get_connection('bad-id')


def test_postgresql_uses_username_key_fallback():
    """Config key 'username' is accepted when 'user' is absent."""
    cfg = {'host': 'localhost', 'database': 'db', 'username': 'alice', 'password': 'pw'}
    row = _make_row('postgresql')
    with _db_patch(row), \
         patch('flowforge.crypto.decrypt_config', return_value=cfg), \
         patch('flowforge.connections.postgres.PostgreSQLConnection.__init__', return_value=None):
        from flowforge.connections.factory import get_connection
        from flowforge.connections.postgres import PostgreSQLConnection
        conn = get_connection('pg-id-2')
        assert isinstance(conn, PostgreSQLConnection)
