"""Unit tests for OracleConnection (connections/oracle.py).

Uses sys.modules patching to mock oracledb — no Oracle Instant Client required.
"""
import sys
from unittest.mock import MagicMock, patch
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_pools():
    """Clear the module-level _pools dict before each test."""
    import flowforge.connections.oracle as oracle_mod
    oracle_mod._pools.clear()
    yield
    oracle_mod._pools.clear()


@pytest.fixture()
def mock_oracledb():
    """Return a MagicMock oracledb and patch it into sys.modules."""
    fake = MagicMock()
    fake_pool = MagicMock()
    fake_conn = MagicMock()
    fake_pool.acquire.return_value = fake_conn
    fake.create_pool.return_value = fake_pool

    with patch.dict(sys.modules, {'oracledb': fake}):
        yield fake, fake_pool, fake_conn


def _make_conn(mock_oracledb):
    """Instantiate OracleConnection with fake oracledb in place."""
    _fake, _pool, _conn = mock_oracledb
    from flowforge.connections.oracle import OracleConnection
    conn = OracleConnection(
        host='db.example.com',
        port=1521,
        service_name='ORCLPDB1',
        user='oracle_user',
        password='secret',
    )
    return conn, _pool, _conn


def _make_cursor(fake_conn):
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value = fake_cursor
    return fake_cursor


# ── Import error ──────────────────────────────────────────────────────────────

def test_import_error_when_oracledb_missing():
    """OracleConnection.__init__ raises ImportError when oracledb is not installed."""
    from flowforge.connections.oracle import OracleConnection
    with patch.dict(sys.modules, {'oracledb': None}):
        with pytest.raises(ImportError, match='python-oracledb'):
            OracleConnection('host', 1521, 'svc', 'user', 'pass')


def test_import_error_message_mentions_install():
    """ImportError message includes an install hint."""
    from flowforge.connections.oracle import OracleConnection
    with patch.dict(sys.modules, {'oracledb': None}):
        try:
            OracleConnection('host', 1521, 'svc', 'user', 'pass')
        except ImportError as exc:
            assert 'pip install' in str(exc).lower()
        else:
            pytest.fail('Expected ImportError was not raised')


# ── Pool registration ─────────────────────────────────────────────────────────

def test_pool_registered_on_first_connect(mock_oracledb):
    import flowforge.connections.oracle as oracle_mod
    _make_conn(mock_oracledb)
    assert len(oracle_mod._pools) == 1


def test_pool_key_uses_host_port_service_user(mock_oracledb):
    import flowforge.connections.oracle as oracle_mod
    _make_conn(mock_oracledb)
    key = list(oracle_mod._pools.keys())[0]
    host, port, service_name, user, _password = key
    assert host == 'db.example.com'
    assert port == 1521
    assert service_name == 'ORCLPDB1'
    assert user == 'oracle_user'


def test_pool_key_includes_password_for_isolation(mock_oracledb):
    import flowforge.connections.oracle as oracle_mod
    _make_conn(mock_oracledb)
    key = list(oracle_mod._pools.keys())[0]
    _host, _port, _svc, _user, password = key
    assert password == 'secret'


def test_same_credentials_reuse_pool(mock_oracledb):
    import flowforge.connections.oracle as oracle_mod
    from flowforge.connections.oracle import OracleConnection
    OracleConnection('db.example.com', 1521, 'ORCLPDB1', 'oracle_user', 'secret')
    OracleConnection('db.example.com', 1521, 'ORCLPDB1', 'oracle_user', 'secret')
    assert len(oracle_mod._pools) == 1


def test_different_host_creates_new_pool_entry(mock_oracledb):
    import flowforge.connections.oracle as oracle_mod
    from flowforge.connections.oracle import OracleConnection
    OracleConnection('host1', 1521, 'svc', 'user', 'pass')
    OracleConnection('host2', 1521, 'svc', 'user', 'pass')
    assert len(oracle_mod._pools) == 2


def test_create_pool_uses_dsn_format(mock_oracledb):
    """Pool is created with host:port/service_name DSN."""
    fake_oracledb, _pool, _conn = mock_oracledb
    from flowforge.connections.oracle import OracleConnection
    OracleConnection('myhost', 1521, 'MYSERVICE', 'myuser', 'mypass')
    kwargs = fake_oracledb.create_pool.call_args.kwargs
    assert kwargs['dsn'] == 'myhost:1521/MYSERVICE'


def test_create_pool_min_max_increment(mock_oracledb):
    """Pool is created with min=1, max=5, increment=1."""
    fake_oracledb, _pool, _conn = mock_oracledb
    from flowforge.connections.oracle import OracleConnection
    OracleConnection('host', 1521, 'svc', 'user', 'pass')
    kwargs = fake_oracledb.create_pool.call_args.kwargs
    assert kwargs['min'] == 1
    assert kwargs['max'] == 5
    assert kwargs['increment'] == 1


def test_autocommit_disabled_on_acquire(mock_oracledb):
    """Acquired connection must have autocommit = False."""
    _fake, _pool, fake_conn = mock_oracledb
    _make_conn(mock_oracledb)
    assert fake_conn.autocommit is False


# ── make_placeholders ─────────────────────────────────────────────────────────

def test_make_placeholders_one(mock_oracledb):
    conn, _, _ = _make_conn(mock_oracledb)
    assert conn.make_placeholders(1) == ':1'


def test_make_placeholders_three(mock_oracledb):
    conn, _, _ = _make_conn(mock_oracledb)
    assert conn.make_placeholders(3) == ':1, :2, :3'


def test_make_placeholders_zero(mock_oracledb):
    conn, _, _ = _make_conn(mock_oracledb)
    assert conn.make_placeholders(0) == ''


# ── execute_procedure ─────────────────────────────────────────────────────────

def test_execute_procedure_builds_begin_end_sql(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    conn.execute_procedure('pkg.proc', {'p1': 'v1', 'p2': 'v2'})
    sql_called = fake_cursor.execute.call_args[0][0]
    assert sql_called.startswith('BEGIN pkg.proc(')
    assert sql_called.endswith('; END;')


def test_execute_procedure_passes_params_dict(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    params = {'run_id': 'abc', 'period': '2026-05'}
    conn.execute_procedure('my_proc', params)
    passed_params = fake_cursor.execute.call_args[0][1]
    assert passed_params == params


def test_execute_procedure_calls_commit(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    _make_cursor(fake_conn)
    conn.execute_procedure('my_proc', {})
    fake_conn.commit.assert_called_once()


def test_execute_procedure_sets_arraysize(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    conn.execute_procedure('my_proc', {})
    assert fake_cursor.arraysize == 1000


def test_execute_procedure_empty_params_builds_valid_sql(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    conn.execute_procedure('pkg.no_args', {})
    sql_called = fake_cursor.execute.call_args[0][0]
    assert sql_called == 'BEGIN pkg.no_args(); END;'


# ── execute_query ─────────────────────────────────────────────────────────────

def test_execute_query_calls_cursor_execute(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = []
    conn.execute_query('SELECT 1 FROM DUAL')
    fake_cursor.execute.assert_called_once_with('SELECT 1 FROM DUAL', ())


def test_execute_query_returns_list(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = [(1,), (2,)]
    result = conn.execute_query('SELECT id FROM t')
    assert isinstance(result, list)
    assert len(result) == 2


def test_execute_query_reads_lob_columns(mock_oracledb):
    """Columns with a .read() method (LOBs) are read transparently."""
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    lob = MagicMock()
    lob.read.return_value = 'LOB content'
    fake_cursor.fetchall.return_value = [(lob,)]
    result = conn.execute_query('SELECT clob_col FROM t')
    assert result == [('LOB content',)]
    lob.read.assert_called_once()


def test_execute_query_passes_params(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = []
    conn.execute_query('SELECT * FROM t WHERE id = :1', (42,))
    fake_cursor.execute.assert_called_once_with('SELECT * FROM t WHERE id = :1', (42,))


def test_execute_query_sets_arraysize(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = []
    conn.execute_query('SELECT 1 FROM DUAL')
    assert fake_cursor.arraysize == 1000


def test_execute_query_non_lob_columns_unchanged(mock_oracledb):
    """Regular columns (no .read()) are returned as-is."""
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = [(42, 'hello')]
    result = conn.execute_query('SELECT id, name FROM t')
    assert result == [(42, 'hello')]


# ── execute_query_with_columns ────────────────────────────────────────────────

def test_execute_query_with_columns_returns_rows_and_cols(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.description = [('ID', None), ('NAME', None)]
    fake_cursor.fetchall.return_value = [(1, 'Alice')]
    rows, cols = conn.execute_query_with_columns('SELECT id, name FROM t')
    assert cols == ['ID', 'NAME']
    assert rows == [(1, 'Alice')]


def test_execute_query_with_columns_no_description(mock_oracledb):
    """None description (DDL or empty cursor) returns empty column list."""
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.description = None
    fake_cursor.fetchall.return_value = []
    rows, cols = conn.execute_query_with_columns('SELECT 1 FROM DUAL')
    assert cols == []
    assert rows == []


def test_execute_query_with_columns_reads_lobs(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    lob = MagicMock()
    lob.read.return_value = 'clob data'
    fake_cursor.description = [('CLOB_COL', None)]
    fake_cursor.fetchall.return_value = [(lob,)]
    rows, cols = conn.execute_query_with_columns('SELECT clob_col FROM t')
    assert rows == [('clob data',)]
    assert cols == ['CLOB_COL']


def test_execute_query_with_columns_sets_arraysize(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.description = []
    fake_cursor.fetchall.return_value = []
    conn.execute_query_with_columns('SELECT 1 FROM DUAL')
    assert fake_cursor.arraysize == 1000


# ── execute_write ─────────────────────────────────────────────────────────────

def test_execute_write_returns_rowcount(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.rowcount = 5
    rows = conn.execute_write('DELETE FROM t WHERE id = :1', (1,))
    assert rows == 5


def test_execute_write_calls_commit(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.rowcount = 1
    conn.execute_write('INSERT INTO t VALUES (:1)', ('x',))
    fake_conn.commit.assert_called_once()


def test_execute_write_passes_params(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.rowcount = 1
    conn.execute_write('UPDATE t SET v = :1 WHERE id = :2', ('val', 99))
    fake_cursor.execute.assert_called_once_with(
        'UPDATE t SET v = :1 WHERE id = :2', ('val', 99)
    )


# ── execute_many ──────────────────────────────────────────────────────────────

def test_execute_many_calls_executemany(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.rowcount = 3
    rows = [('a',), ('b',), ('c',)]
    count = conn.execute_many('INSERT INTO t VALUES (:1)', rows)
    fake_cursor.executemany.assert_called_once_with('INSERT INTO t VALUES (:1)', rows)
    assert count == 3


def test_execute_many_calls_commit(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.rowcount = 2
    conn.execute_many('INSERT INTO t VALUES (:1)', [('x',), ('y',)])
    fake_conn.commit.assert_called_once()


def test_execute_many_returns_rowcount(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.rowcount = 7
    count = conn.execute_many('INSERT INTO t VALUES (:1)', [('x',)] * 7)
    assert count == 7


# ── test() method ─────────────────────────────────────────────────────────────

def test_test_returns_true_on_success(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = [(1,)]
    ok, latency = conn.test()
    assert ok is True
    assert isinstance(latency, int)
    assert latency >= 0


def test_test_queries_dual(mock_oracledb):
    """test() must use SELECT 1 FROM DUAL (Oracle liveness check)."""
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = [(1,)]
    conn.test()
    sql_called = fake_cursor.execute.call_args[0][0]
    assert 'DUAL' in sql_called


def test_test_returns_false_on_failure(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.execute.side_effect = Exception('ORA-12541: no listener')
    ok, latency = conn.test()
    assert ok is False
    assert latency == 0


def test_test_latency_is_non_negative(mock_oracledb):
    conn, _, fake_conn = _make_conn(mock_oracledb)
    fake_cursor = _make_cursor(fake_conn)
    fake_cursor.fetchall.return_value = [(1,)]
    _, latency = conn.test()
    assert latency >= 0


# ── close() ───────────────────────────────────────────────────────────────────

def test_close_releases_connection_to_pool(mock_oracledb):
    """Oracle uses pool.release(conn), not conn.close()."""
    conn, fake_pool, fake_conn = _make_conn(mock_oracledb)
    conn.close()
    fake_pool.release.assert_called_once_with(fake_conn)


def test_close_does_not_call_conn_close(mock_oracledb):
    """conn.close() must NOT be called — pool.release() is the correct Oracle teardown."""
    conn, _pool, fake_conn = _make_conn(mock_oracledb)
    conn.close()
    fake_conn.close.assert_not_called()
