"""Unit tests for flowforge/engine/settings.py — DB override resolution with
env-var fallback. DB access is mocked; these don't need a real app context."""
import os
from unittest.mock import MagicMock, patch


def _mock_row(**overrides):
    row = MagicMock()
    row.run_retention_days = overrides.get('run_retention_days')
    row.audit_retention_days = overrides.get('audit_retention_days')
    row.output_ttl_days = overrides.get('output_ttl_days')
    return row


def _mock_db(get_return_value=None):
    mock_db = MagicMock()
    mock_db.session.get.return_value = get_return_value
    return mock_db


# ── get_run_retention_days ────────────────────────────────────────────────────

def test_run_retention_uses_db_override_when_set():
    from flowforge.engine import settings as settings_mod
    with patch('flowforge.db.models.db', _mock_db(_mock_row(run_retention_days=15))):
        assert settings_mod.get_run_retention_days() == 15


def test_run_retention_falls_back_to_env_when_column_null():
    from flowforge.engine import settings as settings_mod
    with patch('flowforge.db.models.db', _mock_db(_mock_row(run_retention_days=None))), \
         patch.dict(os.environ, {'FLOWFORGE_RUN_RETENTION_DAYS': '77'}):
        assert settings_mod.get_run_retention_days() == 77


def test_run_retention_falls_back_to_env_when_no_row():
    from flowforge.engine import settings as settings_mod
    with patch('flowforge.db.models.db', _mock_db(get_return_value=None)), \
         patch.dict(os.environ, {'FLOWFORGE_RUN_RETENTION_DAYS': '33'}):
        assert settings_mod.get_run_retention_days() == 33


def test_run_retention_falls_back_to_hardcoded_default():
    from flowforge.engine import settings as settings_mod
    env_clean = {k: v for k, v in os.environ.items() if k != 'FLOWFORGE_RUN_RETENTION_DAYS'}
    with patch('flowforge.db.models.db', _mock_db(get_return_value=None)), \
         patch.dict(os.environ, env_clean, clear=True):
        assert settings_mod.get_run_retention_days() == 90


def test_run_retention_falls_back_to_env_when_db_unreachable():
    """No app context / DB error inside _singleton_row() must not raise — just use env."""
    from flowforge.engine import settings as settings_mod
    broken_db = MagicMock()
    broken_db.session.get.side_effect = RuntimeError('Working outside of application context')
    with patch('flowforge.db.models.db', broken_db), \
         patch.dict(os.environ, {'FLOWFORGE_RUN_RETENTION_DAYS': '55'}):
        assert settings_mod.get_run_retention_days() == 55


# ── get_audit_retention_days ──────────────────────────────────────────────────

def test_audit_retention_uses_db_override_when_set():
    from flowforge.engine import settings as settings_mod
    with patch('flowforge.db.models.db', _mock_db(_mock_row(audit_retention_days=8))):
        assert settings_mod.get_audit_retention_days() == 8


def test_audit_retention_falls_back_to_run_retention_env():
    from flowforge.engine import settings as settings_mod
    env = {'FLOWFORGE_RUN_RETENTION_DAYS': '40'}
    env_clean = {k: v for k, v in os.environ.items() if k != 'FLOWFORGE_AUDIT_RETENTION_DAYS'}
    with patch('flowforge.db.models.db', _mock_db(get_return_value=None)), \
         patch.dict(os.environ, {**env_clean, **env}, clear=True):
        assert settings_mod.get_audit_retention_days() == 40


# ── get_output_ttl_days ────────────────────────────────────────────────────────

def test_output_ttl_uses_db_override_when_set():
    from flowforge.engine import settings as settings_mod
    with patch('flowforge.db.models.db', _mock_db(_mock_row(output_ttl_days=2))):
        assert settings_mod.get_output_ttl_days() == 2


def test_output_ttl_falls_back_to_env():
    from flowforge.engine import settings as settings_mod
    with patch('flowforge.db.models.db', _mock_db(get_return_value=None)), \
         patch.dict(os.environ, {'FLOWFORGE_OUTPUT_TTL_DAYS': '9'}):
        assert settings_mod.get_output_ttl_days() == 9


def test_output_ttl_falls_back_to_cleanup_default():
    from flowforge.engine import settings as settings_mod
    from flowforge.engine.cleanup import _DEFAULT_TTL_DAYS
    env_clean = {k: v for k, v in os.environ.items() if k != 'FLOWFORGE_OUTPUT_TTL_DAYS'}
    with patch('flowforge.db.models.db', _mock_db(get_return_value=None)), \
         patch.dict(os.environ, env_clean, clear=True):
        assert settings_mod.get_output_ttl_days() == _DEFAULT_TTL_DAYS
