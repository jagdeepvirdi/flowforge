"""Tests for DbHealthCheckStep branches not covered by test_db_health_check.py:
MySQL, class-name db_type detection, exception paths.
"""
import os
from unittest.mock import MagicMock, patch

from flowforge.steps.db_health_check import DbHealthCheckStep


def _make_conn(db_type, query_results, *, raise_on=None):
    conn = MagicMock()
    conn.db_type = db_type
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)

    def execute_query(sql):
        if raise_on and raise_on.lower() in sql.lower():
            raise Exception(f'Simulated error on {raise_on}')
        for key, val in query_results.items():
            if key.lower() in sql.lower():
                return val
        return [[None]]

    conn.execute_query.side_effect = execute_query
    return conn


# ── MySQL ─────────────────────────────────────────────────────────────────────

def test_mysql_health_check(tmp_path):
    results = {'threads_connected': [['Threads_connected', 42]]}
    conn = _make_conn('mysql', results)
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'my-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success
    assert 'MySQL Health Check' in result.logs
    assert 'Connected Threads: 42' in result.logs


def test_mysql_health_check_no_threads_row(tmp_path):
    # Use a direct MagicMock so return_value isn't shadowed by side_effect
    conn = MagicMock()
    conn.db_type = 'mysql'
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute_query.return_value = []  # SHOW STATUS returns empty list → N/A
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'my-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success
    assert 'N/A' in result.logs


# ── db_type detection via class name ──────────────────────────────────────────

def test_db_type_inferred_from_postgres_class_name(tmp_path):
    conn = _make_conn(None, {
        'pg_stat_activity': [[2]],
        'pg_statio_user_tables': [[0, 0]],
        'pg_stat_replication': [],
    })
    conn.__class__ = type('PostgreSQLConnection', (), {})
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'x'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success
    assert 'PostgreSQL' in result.logs


def test_db_type_inferred_from_oracle_class_name(tmp_path):
    conn = _make_conn(None, {
        'v$session': [[1]],
        'v$sysstat': [[90.0]],
        'dba_tablespace_usage_metrics': [],
    })
    conn.__class__ = type('OracleConnection', (), {})
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'x'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success
    assert 'Oracle' in result.logs


def test_db_type_inferred_from_mysql_class_name(tmp_path):
    conn = _make_conn(None, {'threads_connected': [['Threads_connected', 5]]})
    conn.__class__ = type('MySQLConnection', (), {})
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'x'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success


# ── Oracle exception branches ──────────────────────────────────────────────────

def test_oracle_buffer_cache_exception_is_swallowed(tmp_path):
    """Exception querying v$sysstat must not fail the step."""
    conn = _make_conn('oracle', {'v$session': [[3]], 'dba_tablespace_usage_metrics': []},
                      raise_on='v$sysstat')
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'ora-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success


def test_oracle_tablespace_exception_is_swallowed(tmp_path):
    """Exception querying dba_tablespace_usage_metrics must not fail the step."""
    conn = _make_conn('oracle', {'v$session': [[3]], 'v$sysstat': [[88.0]]},
                      raise_on='dba_tablespace_usage_metrics')
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'ora-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success


# ── PostgreSQL replication exception swallowed ────────────────────────────────

def test_postgres_replication_exception_is_swallowed(tmp_path):
    conn = _make_conn('postgresql', {
        'pg_stat_activity': [[4]],
        'pg_statio_user_tables': [[100, 900]],
    }, raise_on='pg_stat_replication')
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'pg-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success


# ── Top-level exception ───────────────────────────────────────────────────────

def test_step_returns_failure_on_connection_error():
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'bad-conn'})

    with patch('flowforge.connections.factory.get_connection',
               side_effect=Exception('connection refused')):
        result = step.run({'steps': {}})

    assert not result.success
    assert 'error' in result.error.lower()


# ── Zero cache read+hit (zero-total branch) ───────────────────────────────────

def test_postgres_zero_total_cache_skips_ratio_section(tmp_path):
    results = {
        'pg_stat_activity': [[1]],
        'pg_statio_user_tables': [[0, 0]],   # total = 0, ratio skipped
        'pg_stat_replication': [],
    }
    conn = _make_conn('postgresql', results)
    step = DbHealthCheckStep(name='chk', config={'connection_id': 'pg-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-06-08', 'steps': {}})

    assert result.success
    assert 'Cache' not in result.logs
