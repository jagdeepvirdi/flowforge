"""Unit tests for flowforge/connections/redshift.py — Redshift is a thin
PostgreSQL-wire-compatible subclass, so these tests mainly confirm the
type tag, default port, and that it inherits behavior from PostgreSQLConnection.
"""
from unittest.mock import MagicMock, patch


def test_redshift_is_postgresql_subclass():
    from flowforge.connections.postgres import PostgreSQLConnection
    from flowforge.connections.redshift import RedshiftConnection
    assert issubclass(RedshiftConnection, PostgreSQLConnection)


def test_redshift_db_type():
    from flowforge.connections.redshift import RedshiftConnection
    assert RedshiftConnection.db_type == 'redshift'


def test_redshift_default_port_is_5439():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    with patch('flowforge.connections.postgres.pool.ThreadedConnectionPool', return_value=mock_pool) as mock_pool_class:
        from flowforge.connections.redshift import RedshiftConnection
        RedshiftConnection(host='redshift-cluster.example.com', database='dev', user='u', password='p')
        _, kwargs = mock_pool_class.call_args
        assert kwargs['port'] == 5439


def test_redshift_explicit_port_overrides_default():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    with patch('flowforge.connections.postgres.pool.ThreadedConnectionPool', return_value=mock_pool) as mock_pool_class:
        from flowforge.connections.redshift import RedshiftConnection
        RedshiftConnection(host='h', database='d', user='u', password='p', port=5555)
        _, kwargs = mock_pool_class.call_args
        assert kwargs['port'] == 5555


def test_redshift_inherits_execute_query():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1,)]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_pool.getconn.return_value = mock_conn
    with patch('flowforge.connections.postgres.pool.ThreadedConnectionPool', return_value=mock_pool):
        from flowforge.connections.redshift import RedshiftConnection
        conn = RedshiftConnection(host='h', database='d', user='u', password='p')
        rows = conn.execute_query("SELECT 1")
        assert rows == [(1,)]


def test_redshift_make_placeholders_uses_percent_s():
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = MagicMock()
    with patch('flowforge.connections.postgres.pool.ThreadedConnectionPool', return_value=mock_pool):
        from flowforge.connections.redshift import RedshiftConnection
        conn = RedshiftConnection(host='h', database='d', user='u', password='p')
        assert conn.make_placeholders(3) == '%s, %s, %s'
