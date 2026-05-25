"""Unit tests for MySQLConnection (connections/mysql.py).

Uses sys.modules patching to mock pymysql — no real MySQL required.
"""
import sys
from unittest.mock import MagicMock, patch, call
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_pools():
    """Clear the module-level _pools dict before each test."""
    import flowforge.connections.mysql as mysql_mod
    mysql_mod._pools.clear()
    yield
    mysql_mod._pools.clear()


@pytest.fixture()
def mock_pymysql():
    """Return a MagicMock pymysql and patch it into sys.modules."""
    fake = MagicMock()
    fake_conn = MagicMock()
    fake.connect.return_value = fake_conn
    fake.cursors = MagicMock()
    fake.cursors.Cursor = MagicMock()

    modules = {
        'pymysql': fake,
        'pymysql.connections': MagicMock(),
        'pymysql.cursors': MagicMock(),
    }
    with patch.dict(sys.modules, modules):
        yield fake, fake_conn


def _make_conn(mock_pymysql):
    """Instantiate MySQLConnection with the fake pymysql in place."""
    fake_pymysql, fake_conn = mock_pymysql
    from flowforge.connections.mysql import MySQLConnection
    conn = MySQLConnection(
        host='db.example.com',
        database='mydb',
        user='user',
        password='secret',
        port=3306,
    )
    return conn, fake_conn


# ── Import error ──────────────────────────────────────────────────────────────

def test_import_error_when_pymysql_missing():
    """MySQLConnection.__init__ raises ImportError when pymysql is not installed."""
    from flowforge.connections.mysql import MySQLConnection
    with patch.dict(sys.modules, {'pymysql': None, 'pymysql.connections': None,
                                   'pymysql.cursors': None}):
        with pytest.raises(ImportError, match='PyMySQL'):
            MySQLConnection('host', 'db', 'user', 'pass')


def test_import_error_message_mentions_install():
    """ImportError message includes install hint."""
    from flowforge.connections.mysql import MySQLConnection
    with patch.dict(sys.modules, {'pymysql': None, 'pymysql.connections': None,
                                   'pymysql.cursors': None}):
        try:
            MySQLConnection('host', 'db', 'user', 'pass')
        except ImportError as exc:
            assert 'pip install' in str(exc).lower() or 'mysql' in str(exc).lower()
        else:
            pytest.fail('Expected ImportError was not raised')


# ── Pool registration ─────────────────────────────────────────────────────────

def test_pool_registered_on_first_connect(mock_pymysql):
    import flowforge.connections.mysql as mysql_mod
    _make_conn(mock_pymysql)
    assert len(mysql_mod._pools) == 1


def test_pool_key_uses_host_port_db_user(mock_pymysql):
    import flowforge.connections.mysql as mysql_mod
    _make_conn(mock_pymysql)
    key = list(mysql_mod._pools.keys())[0]
    host, port, database, user, _pw_hash = key
    assert host == 'db.example.com'
    assert port == 3306
    assert database == 'mydb'
    assert user == 'user'


def test_pool_key_uses_hashed_password_not_plaintext(mock_pymysql):
    import flowforge.connections.mysql as mysql_mod
    _make_conn(mock_pymysql)
    key = list(mysql_mod._pools.keys())[0]
    _host, _port, _db, _user, pw_hash = key
    assert pw_hash != 'secret'
    assert len(pw_hash) == 16


def test_same_credentials_reuse_pool(mock_pymysql):
    import flowforge.connections.mysql as mysql_mod
    from flowforge.connections.mysql import MySQLConnection
    fake_pymysql, _ = mock_pymysql
    MySQLConnection('db.example.com', 'mydb', 'user', 'secret')
    MySQLConnection('db.example.com', 'mydb', 'user', 'secret')
    assert len(mysql_mod._pools) == 1


def test_different_host_creates_new_pool_entry(mock_pymysql):
    import flowforge.connections.mysql as mysql_mod
    from flowforge.connections.mysql import MySQLConnection
    MySQLConnection('host1', 'mydb', 'user', 'pass')
    MySQLConnection('host2', 'mydb', 'user', 'pass')
    assert len(mysql_mod._pools) == 2


# ── make_placeholders ─────────────────────────────────────────────────────────

def test_make_placeholders_one(mock_pymysql):
    conn, _ = _make_conn(mock_pymysql)
    assert conn.make_placeholders(1) == '%s'


def test_make_placeholders_three(mock_pymysql):
    conn, _ = _make_conn(mock_pymysql)
    assert conn.make_placeholders(3) == '%s, %s, %s'


def test_make_placeholders_zero(mock_pymysql):
    conn, _ = _make_conn(mock_pymysql)
    assert conn.make_placeholders(0) == ''


# ── execute_query ─────────────────────────────────────────────────────────────

def test_execute_query_calls_cursor_execute(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.fetchall.return_value = [(1,), (2,)]
    fake_conn.cursor.return_value = fake_cursor

    result = conn.execute_query('SELECT 1')
    fake_cursor.execute.assert_called_once_with('SELECT 1', ())
    assert result == [(1,), (2,)]


def test_execute_query_returns_list(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.fetchall.return_value = []
    fake_conn.cursor.return_value = fake_cursor

    result = conn.execute_query('SELECT * FROM empty')
    assert isinstance(result, list)


# ── execute_write ─────────────────────────────────────────────────────────────

def test_execute_write_returns_rowcount(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.rowcount = 7
    fake_conn.cursor.return_value = fake_cursor

    rows = conn.execute_write('DELETE FROM t WHERE x = %s', (1,))
    assert rows == 7


def test_execute_write_calls_commit(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.rowcount = 1
    fake_conn.cursor.return_value = fake_cursor

    conn.execute_write('INSERT INTO t VALUES (%s)', ('x',))
    fake_conn.commit.assert_called()


# ── execute_many ──────────────────────────────────────────────────────────────

def test_execute_many_calls_executemany(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.rowcount = 3
    fake_conn.cursor.return_value = fake_cursor

    rows = [('a',), ('b',), ('c',)]
    count = conn.execute_many('INSERT INTO t VALUES (%s)', rows)
    fake_cursor.executemany.assert_called_once_with('INSERT INTO t VALUES (%s)', rows)
    assert count == 3


def test_execute_many_calls_commit(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.rowcount = 2
    fake_conn.cursor.return_value = fake_cursor

    conn.execute_many('INSERT INTO t VALUES (%s)', [('x',), ('y',)])
    fake_conn.commit.assert_called()


# ── test() method ─────────────────────────────────────────────────────────────

def test_test_returns_true_on_success(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.fetchall.return_value = [(1,)]
    fake_conn.cursor.return_value = fake_cursor

    ok, latency = conn.test()
    assert ok is True
    assert isinstance(latency, int)
    assert latency >= 0


def test_test_returns_false_on_failure(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_cursor.execute.side_effect = Exception('Connection refused')
    fake_conn.cursor.return_value = fake_cursor

    ok, latency = conn.test()
    assert ok is False
    assert latency == 0


# ── close() ───────────────────────────────────────────────────────────────────

def test_close_calls_conn_close(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    conn.close()
    fake_conn.close.assert_called_once()


def test_close_does_not_raise_on_error(mock_pymysql):
    conn, fake_conn = _make_conn(mock_pymysql)
    fake_conn.close.side_effect = Exception('already closed')
    conn.close()   # should not raise
