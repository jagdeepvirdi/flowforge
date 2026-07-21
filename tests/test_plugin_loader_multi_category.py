"""Tests for engine/loader.py's generalized plugin scanner (Phase 13.3 ARCH-7/ARCH-8):
a single plugin file (or entry point) can register a step, a connection, or an
email provider — not just steps — and pip-installed plugins can self-register
via the `flowforge.plugins` entry-point group.
"""
import importlib.metadata
import textwrap
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_plugins():
    from flowforge.engine.loader import _reset_plugin_state_for_tests
    _reset_plugin_state_for_tests()
    yield
    _reset_plugin_state_for_tests()


def _write_plugin(tmp_path, filename, content):
    (tmp_path / filename).write_text(textwrap.dedent(content))


# ── plugin-defined connections ─────────────────────────────────────────────────

_CONNECTION_PLUGIN = """
    from typing import Any
    from flowforge.connections.base import BaseConnection

    class MyConnection(BaseConnection):
        db_type = 'my_custom_db'

        def __init__(self, host):
            self.host = host

        @classmethod
        def from_config(cls, cfg):
            return cls(host=cfg['host'])

        def execute_procedure(self, name, params): pass
        def execute_query(self, sql, params=()): return []
        def execute_query_with_columns(self, sql, params=()): return [], []
        def execute_write(self, sql, params=()): return 0
        def execute_many(self, sql, rows): return 0
        def make_placeholders(self, n): return ''
        def test(self): return True, 0
        def close(self): pass
"""


def test_plugin_connection_registers(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'my_conn_plugin.py', _CONNECTION_PLUGIN)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.connections.factory import connections_registry
    from flowforge.engine.loader import _load_plugins
    _load_plugins()
    assert 'my_custom_db' in connections_registry
    cls = connections_registry.get('my_custom_db')
    assert cls.__name__ == 'MyConnection'


def test_plugin_connection_usable_via_get_connection(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'my_conn_plugin.py', _CONNECTION_PLUGIN)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _load_plugins
    _load_plugins()

    row = MagicMock()
    row.db_type = 'my_custom_db'
    row.config = {}
    mock_db = MagicMock()
    mock_db.session.get.return_value = row
    with patch('flowforge.db.models.db', mock_db), \
         patch('flowforge.crypto.decrypt_config', return_value={'host': 'plugin-host'}):
        from flowforge.connections.factory import get_connection
        conn = get_connection('some-id')
    assert conn.host == 'plugin-host'


def test_plugin_connection_conflicting_db_type_is_skipped(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'conflict_conn_plugin.py', """
        from flowforge.connections.base import BaseConnection

        class ConflictConnection(BaseConnection):
            db_type = 'postgresql'  # collides with a built-in

            def execute_procedure(self, name, params): pass
            def execute_query(self, sql, params=()): return []
            def execute_query_with_columns(self, sql, params=()): return [], []
            def execute_write(self, sql, params=()): return 0
            def execute_many(self, sql, rows): return 0
            def make_placeholders(self, n): return ''
            def test(self): return True, 0
            def close(self): pass
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.connections.factory import connections_registry
    from flowforge.engine.loader import _load_plugins
    _load_plugins()
    entry = connections_registry.get('postgresql')
    assert isinstance(entry, tuple), "built-in postgresql registration must not be overwritten"


def test_plugin_connection_missing_db_type_is_skipped(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'no_type_conn_plugin.py', """
        from flowforge.connections.base import BaseConnection

        class NoTypeConnection(BaseConnection):
            def execute_procedure(self, name, params): pass
            def execute_query(self, sql, params=()): return []
            def execute_query_with_columns(self, sql, params=()): return [], []
            def execute_write(self, sql, params=()): return 0
            def execute_many(self, sql, rows): return 0
            def make_placeholders(self, n): return ''
            def test(self): return True, 0
            def close(self): pass
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.connections.factory import connections_registry
    from flowforge.engine.loader import _load_plugins
    _load_plugins()
    assert len(connections_registry) == 8  # only the built-ins


def test_plugin_connection_without_from_config_raises_at_use_time(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'no_from_config_plugin.py', """
        from flowforge.connections.base import BaseConnection

        class NoFromConfigConnection(BaseConnection):
            db_type = 'no_from_config_db'

            def execute_procedure(self, name, params): pass
            def execute_query(self, sql, params=()): return []
            def execute_query_with_columns(self, sql, params=()): return [], []
            def execute_write(self, sql, params=()): return 0
            def execute_many(self, sql, rows): return 0
            def make_placeholders(self, n): return ''
            def test(self): return True, 0
            def close(self): pass
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _load_plugins
    _load_plugins()

    row = MagicMock()
    row.db_type = 'no_from_config_db'
    row.config = {}
    mock_db = MagicMock()
    mock_db.session.get.return_value = row
    with patch('flowforge.db.models.db', mock_db), \
         patch('flowforge.crypto.decrypt_config', return_value={}):
        from flowforge.connections.factory import get_connection
        with pytest.raises(ValueError, match='from_config'):
            get_connection('some-id')


# ── plugin-defined email providers ─────────────────────────────────────────────

_PROVIDER_PLUGIN = """
    from flowforge.email_providers.base import EmailProvider, EmailResult

    class MyProvider(EmailProvider):
        provider_type = 'my_custom_provider'

        def __init__(self, api_key):
            self.api_key = api_key

        @classmethod
        def from_config(cls, cfg):
            return cls(api_key=cfg['api_key'])

        def send(self, to, cc, bcc, subject, html_body, attachments):
            return EmailResult(success=True, recipients=to)
"""


def test_plugin_provider_registers(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'my_provider_plugin.py', _PROVIDER_PLUGIN)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.email_providers.factory import providers_registry
    from flowforge.engine.loader import _load_plugins
    _load_plugins()
    assert 'my_custom_provider' in providers_registry
    cls = providers_registry.get('my_custom_provider')
    assert cls.__name__ == 'MyProvider'


def test_plugin_provider_usable_via_get_email_provider(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'my_provider_plugin.py', _PROVIDER_PLUGIN)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _load_plugins
    _load_plugins()

    row = MagicMock()
    row.provider_type = 'my_custom_provider'
    row.config = {}
    mock_db = MagicMock()
    mock_db.session.get.return_value = row
    with patch('flowforge.db.models.db', mock_db), \
         patch('flowforge.crypto.decrypt_config', return_value={'api_key': 'secret-key'}):
        from flowforge.email_providers.factory import get_email_provider
        provider = get_email_provider('some-id')
    assert provider.api_key == 'secret-key'


# ── one file, multiple categories ──────────────────────────────────────────────

def test_single_file_registers_step_and_connection(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'mixed_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult
        from flowforge.connections.base import BaseConnection

        class MixedStep(BaseStep):
            step_type = 'mixed_step'

            def run(self, context):
                return StepResult(success=True)

        class MixedConnection(BaseConnection):
            db_type = 'mixed_db'

            def execute_procedure(self, name, params): pass
            def execute_query(self, sql, params=()): return []
            def execute_query_with_columns(self, sql, params=()): return [], []
            def execute_write(self, sql, params=()): return 0
            def execute_many(self, sql, rows): return 0
            def make_placeholders(self, n): return ''
            def test(self): return True, 0
            def close(self): pass
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.connections.factory import connections_registry
    from flowforge.engine.loader import _load_plugins, get_step_types
    _load_plugins()
    assert 'mixed_step' in get_step_types()
    assert 'mixed_db' in connections_registry


# ── entry-point plugins (ARCH-8) ────────────────────────────────────────────────

class _FakeEntryPoint:
    def __init__(self, name, obj=None, load_error=None):
        self.name = name
        self._obj = obj
        self._load_error = load_error

    def load(self):
        if self._load_error:
            raise self._load_error
        return self._obj


def _patched_entry_points(monkeypatch, entry_points):
    def _fake(*, group):
        assert group == 'flowforge.plugins'
        return entry_points
    monkeypatch.setattr(importlib.metadata, 'entry_points', _fake)


def test_entry_point_registers_step(monkeypatch, tmp_path):
    from flowforge.steps.base import BaseStep, StepResult

    class EntryPointStep(BaseStep):
        step_type = 'entry_point_step'

        def run(self, context):
            return StepResult(success=True)

    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))  # empty dir, directory scan is a no-op
    _patched_entry_points(monkeypatch, [_FakeEntryPoint('ep_step', obj=EntryPointStep)])

    from flowforge.engine.loader import _load_plugins, get_step_types
    _load_plugins()
    assert 'entry_point_step' in get_step_types()


def test_entry_point_load_failure_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    _patched_entry_points(monkeypatch, [
        _FakeEntryPoint('broken_ep', load_error=RuntimeError('boom')),
    ])
    from flowforge.engine.loader import _load_plugins, get_step_types
    _load_plugins()  # must not raise
    assert 'db_procedure' in get_step_types()


def test_entry_point_non_class_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    _patched_entry_points(monkeypatch, [_FakeEntryPoint('not_a_class', obj='just a string')])
    from flowforge.engine.loader import _load_plugins, get_step_types
    _load_plugins()  # must not raise
    assert 'db_procedure' in get_step_types()


def test_entry_points_enumeration_failure_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))

    def _raise(*, group):
        raise RuntimeError('metadata backend broken')
    monkeypatch.setattr(importlib.metadata, 'entry_points', _raise)

    from flowforge.engine.loader import _load_plugins, get_step_types
    _load_plugins()  # must not raise
    assert 'db_procedure' in get_step_types()


def test_entry_point_and_directory_plugins_both_load(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'dir_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class DirStep(BaseStep):
            step_type = 'dir_step'

            def run(self, context):
                return StepResult(success=True)
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))

    from flowforge.steps.base import BaseStep, StepResult

    class EpStep(BaseStep):
        step_type = 'ep_step_type'

        def run(self, context):
            return StepResult(success=True)

    _patched_entry_points(monkeypatch, [_FakeEntryPoint('ep', obj=EpStep)])

    from flowforge.engine.loader import _load_plugins, get_step_types
    _load_plugins()
    types = get_step_types()
    assert 'dir_step' in types
    assert 'ep_step_type' in types


# ── reset helper clears all three categories ────────────────────────────────────

def test_reset_clears_plugin_connections_and_providers(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'reset_conn_plugin.py', _CONNECTION_PLUGIN)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.connections.factory import connections_registry
    from flowforge.engine.loader import _load_plugins, _reset_plugin_state_for_tests
    _load_plugins()
    assert 'my_custom_db' in connections_registry

    _reset_plugin_state_for_tests()
    assert 'my_custom_db' not in connections_registry
    assert len(connections_registry) == 8  # built-ins survive
