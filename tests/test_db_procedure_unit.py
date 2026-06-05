"""Unit tests for DbProcedureStep — covers the two previously-uncovered paths:
  1. validate_identifier raises ValueError for an invalid procedure name (lines 20-21)
  2. _get_connection — both the connection_id branch and the env-var fallback (lines 37-45)
"""
from unittest.mock import MagicMock, patch

from flowforge.steps.db_procedure import DbProcedureStep

# ── validate_identifier error path ─────────────────────────────────────────────

class TestInvalidProcedureName:

    def test_sql_injection_attempt_returns_error(self):
        step = DbProcedureStep('proc', {'procedure': "DROP TABLE users; --"})
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        with patch.object(step, '_get_connection', return_value=mock_conn):
            result = step.run({})
        assert result.success is False
        assert 'Invalid' in result.error or 'procedure name' in result.error

    def test_space_in_name_returns_error(self):
        step = DbProcedureStep('proc', {'procedure': 'my proc'})
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        with patch.object(step, '_get_connection', return_value=mock_conn):
            result = step.run({})
        assert result.success is False

    def test_valid_package_proc_name_is_accepted(self):
        step = DbProcedureStep('proc', {
            'procedure': 'pkg_revenue.populate_monthly_summary',
            'connection_id': 'cid',
        })
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        with patch.object(step, '_get_connection', return_value=mock_conn):
            result = step.run({})
        assert result.success is True


# ── _get_connection — connection_id branch ─────────────────────────────────────

class TestGetConnectionWithId:

    def test_delegates_to_factory(self):
        step = DbProcedureStep('proc', {
            'procedure': 'my_proc',
            'connection_id': 'test-uuid-1234',
        })
        mock_conn = MagicMock()
        with patch('flowforge.connections.factory.get_connection', return_value=mock_conn) as mock_factory:
            result_conn = step._get_connection()
        mock_factory.assert_called_once_with('test-uuid-1234')
        assert result_conn is mock_conn


# ── _get_connection — env-var fallback ────────────────────────────────────────

class TestGetConnectionEnvFallback:

    def test_builds_postgres_conn_from_env(self, monkeypatch):
        monkeypatch.setenv('DB_HOST', 'pg.internal')
        monkeypatch.setenv('DB_NAME', 'mydb')
        monkeypatch.setenv('DB_USER', 'svc')
        monkeypatch.setenv('DB_PASSWORD', 'secret')

        step = DbProcedureStep('proc', {'procedure': 'my_proc'})  # no connection_id
        mock_pg = MagicMock()
        with patch('flowforge.connections.postgres.PostgreSQLConnection', return_value=mock_pg) as mock_cls:
            result_conn = step._get_connection()

        mock_cls.assert_called_once_with(
            host='pg.internal',
            database='mydb',
            user='svc',
            password='secret',
        )
        assert result_conn is mock_pg

    def test_uses_empty_strings_when_env_not_set(self, monkeypatch):
        for key in ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'):
            monkeypatch.delenv(key, raising=False)

        step = DbProcedureStep('proc', {'procedure': 'my_proc'})
        mock_pg = MagicMock()
        with patch('flowforge.connections.postgres.PostgreSQLConnection', return_value=mock_pg) as mock_cls:
            step._get_connection()

        kwargs = mock_cls.call_args.kwargs
        assert kwargs['host'] == ''
        assert kwargs['database'] == ''
