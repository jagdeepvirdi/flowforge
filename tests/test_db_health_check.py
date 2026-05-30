"""Tests for DbHealthCheckStep (report-output variant)."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flowforge.steps.db_health_check import DbHealthCheckStep


def _make_conn(db_type: str, query_results: dict):
    """Build a mock connection with execute_query returning per-query-substring results."""
    conn = MagicMock()
    conn.db_type = db_type
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)

    def execute_query(sql):
        sql_lower = sql.lower().strip()
        for key, val in query_results.items():
            if key.lower() in sql_lower:
                return val
        return [[None]]

    conn.execute_query.side_effect = execute_query
    return conn


# ── PostgreSQL ────────────────────────────────────────────────────────────────

def test_postgres_sets_output_path(tmp_path):
    results = {
        'pg_stat_activity': [[5]],
        'pg_statio_user_tables': [[100, 9900]],
        'pg_stat_replication': [],
    }
    conn = _make_conn('postgresql', results)

    step = DbHealthCheckStep(name='db_check', config={'connection_id': 'pg-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert result.output_path
    assert Path(result.output_path).suffix == '.xlsx'
    assert Path(result.output_path).exists()


def test_postgres_logs_summary(tmp_path):
    results = {
        'pg_stat_activity': [[12]],
        'pg_statio_user_tables': [[50, 950]],
        'pg_stat_replication': [],
    }
    conn = _make_conn('postgresql', results)
    step = DbHealthCheckStep(name='db_check', config={'connection_id': 'pg-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert 'PostgreSQL Health Check' in result.logs
    assert 'Active Sessions: 12' in result.logs
    assert 'Cache Hit Ratio' in result.logs


def test_postgres_csv_format(tmp_path):
    results = {
        'pg_stat_activity': [[3]],
        'pg_statio_user_tables': [[0, 0]],
        'pg_stat_replication': [],
    }
    conn = _make_conn('postgresql', results)
    step = DbHealthCheckStep(name='db_check', config={
        'connection_id': 'pg-1',
        'format': 'csv',
    })

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert Path(result.output_path).suffix == '.csv'
    content = Path(result.output_path).read_text()
    assert 'Sessions' in content
    assert 'Active Sessions' in content


def test_postgres_replication_lag_included(tmp_path):
    results = {
        'pg_stat_activity': [[2]],
        'pg_statio_user_tables': [[100, 900]],
        'pg_stat_replication': [['10.0.0.2', 8192], ['10.0.0.3', 4096]],
    }
    conn = _make_conn('postgresql', results)
    step = DbHealthCheckStep(name='db_check', config={'connection_id': 'pg-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert 'Replication Lag' in result.logs


def test_custom_output_filename(tmp_path):
    results = {'pg_stat_activity': [[1]], 'pg_statio_user_tables': [[0, 0]], 'pg_stat_replication': []}
    conn = _make_conn('postgresql', results)
    step = DbHealthCheckStep(name='db_check', config={
        'connection_id': 'pg-1',
        'output_filename': 'mydb_health_{{ current_date }}.xlsx',
    })

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert Path(result.output_path).name == 'mydb_health_2026-05-30.xlsx'


# ── Oracle ────────────────────────────────────────────────────────────────────

def test_oracle_sets_output_path(tmp_path):
    results = {
        'v$session': [[7]],
        'v$sysstat': [[95.5]],
        'dba_tablespace_usage_metrics': [],
    }
    conn = _make_conn('oracle', results)
    step = DbHealthCheckStep(name='db_check', config={'connection_id': 'ora-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert 'Oracle Health Check' in result.logs
    assert 'Active User Sessions: 7' in result.logs


def test_oracle_high_tablespace_included(tmp_path):
    results = {
        'v$session': [[3]],
        'v$sysstat': [[88.0]],
        'dba_tablespace_usage_metrics': [['USERS', 92.5], ['SYSTEM', 85.0]],
    }
    conn = _make_conn('oracle', results)
    step = DbHealthCheckStep(name='db_check', config={'connection_id': 'ora-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'current_date': '2026-05-30', 'steps': {}})

    assert result.success
    assert 'High Tablespace' in result.logs


# ── Error cases ───────────────────────────────────────────────────────────────

def test_missing_connection_id():
    step = DbHealthCheckStep(name='db_check', config={})
    result = step.run({'steps': {}})
    assert not result.success
    assert 'connection_id' in result.error


def test_unsupported_db_type(tmp_path):
    conn = _make_conn('snowflake', {})
    step = DbHealthCheckStep(name='db_check', config={'connection_id': 'sf-1'})

    with patch('flowforge.connections.factory.get_connection', return_value=conn), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_DIR': str(tmp_path)}):
        result = step.run({'steps': {}})

    assert not result.success
    assert 'unsupported' in result.error


def test_step_type_attribute():
    assert DbHealthCheckStep.step_type == 'db_health_check'


def test_loader_registers_db_health_check():
    from flowforge.engine.loader import _STEP_CLASSES
    assert 'db_health_check' in _STEP_CLASSES
