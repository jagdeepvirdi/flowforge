"""Tests for flowforge/engine/loader.py — community plugin step type loading."""
import textwrap

import pytest


@pytest.fixture(autouse=True)
def _reset_plugins():
    from flowforge.engine.loader import _reset_plugin_state_for_tests
    _reset_plugin_state_for_tests()
    yield
    _reset_plugin_state_for_tests()


def _write_plugin(tmp_path, filename, content):
    (tmp_path / filename).write_text(textwrap.dedent(content))


# ── _load_plugins / get_step_types ──────────────────────────────────────────────

def test_missing_plugin_dir_is_noop(monkeypatch, tmp_path):
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path / 'does_not_exist'))
    from flowforge.engine.loader import get_step_types
    types = get_step_types()
    assert 'db_procedure' in types
    assert 'notification' in types


def test_no_plugin_dir_env_var_defaults_and_is_noop(monkeypatch, tmp_path):
    monkeypatch.delenv('FLOWFORGE_PLUGIN_DIR', raising=False)
    monkeypatch.chdir(tmp_path)  # default './plugins' won't exist here
    from flowforge.engine.loader import get_step_types
    assert 'db_procedure' in get_step_types()


def test_loads_valid_plugin(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'my_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class MyStep(BaseStep):
            step_type = 'my_custom_step'

            def run(self, context):
                return StepResult(success=True, logs='ran')
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import get_step_types, is_plugin_step_type
    types = get_step_types()
    assert 'my_custom_step' in types
    assert is_plugin_step_type('my_custom_step') is True
    assert is_plugin_step_type('db_procedure') is False
    assert is_plugin_step_type('not_registered_at_all') is False


def test_plugin_class_instantiates_and_runs(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'my_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class MyStep(BaseStep):
            step_type = 'my_custom_step'

            def run(self, context):
                return StepResult(success=True, logs='ran ok')
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _STEP_CLASSES, _load_plugins
    _load_plugins()
    cls = _STEP_CLASSES['my_custom_step']
    step = cls(name='test', config={'on_error': 'stop'})
    result = step.run({})
    assert result.success is True
    assert result.logs == 'ran ok'


def test_file_starting_with_underscore_is_skipped(monkeypatch, tmp_path):
    _write_plugin(tmp_path, '_helpers.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class HelperStep(BaseStep):
            step_type = 'should_not_register'

            def run(self, context):
                return StepResult(success=True)
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import get_step_types
    assert 'should_not_register' not in get_step_types()


def test_plugin_missing_step_type_is_skipped(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'bad_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class NoTypeStep(BaseStep):
            def run(self, context):
                return StepResult(success=True)
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import get_step_types
    # must not raise, and built-ins are unaffected
    assert 'db_procedure' in get_step_types()


def test_plugin_conflicting_step_type_is_skipped(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'conflict_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class ConflictStep(BaseStep):
            step_type = 'db_procedure'  # collides with a built-in

            def run(self, context):
                return StepResult(success=True)
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _STEP_CLASSES, _load_plugins, is_plugin_step_type
    _load_plugins()
    # built-in registration (dotted path string) must not be overwritten by the plugin class
    assert isinstance(_STEP_CLASSES['db_procedure'], str)
    assert is_plugin_step_type('db_procedure') is False


def test_plugin_file_with_import_error_is_skipped_gracefully(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'broken_plugin.py', """
        import this_module_does_not_exist_anywhere_xyz  # noqa
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import get_step_types
    types = get_step_types()  # must not raise
    assert 'db_procedure' in types


def test_plugin_file_with_no_baseStep_subclass_is_skipped(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'no_step_plugin.py', """
        class NotAStep:
            step_type = 'irrelevant'
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import get_step_types
    assert 'irrelevant' not in get_step_types()


def test_multiple_step_classes_in_one_file_all_register(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'multi_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class FirstStep(BaseStep):
            step_type = 'multi_first'

            def run(self, context):
                return StepResult(success=True)

        class SecondStep(BaseStep):
            step_type = 'multi_second'

            def run(self, context):
                return StepResult(success=True)
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import get_step_types
    types = get_step_types()
    assert 'multi_first' in types
    assert 'multi_second' in types


def test_load_plugins_runs_only_once_per_process(monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'once_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class OnceStep(BaseStep):
            step_type = 'once_step'

            def run(self, context):
                return StepResult(success=True)
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _load_plugins, get_step_types
    _load_plugins()
    assert 'once_step' in get_step_types()

    # Remove the plugin file and re-invoke — already loaded, so this is a no-op
    # and the previously-registered type stays registered.
    (tmp_path / 'once_plugin.py').unlink()
    _load_plugins()
    assert 'once_step' in get_step_types()


def test_get_step_types_is_sorted(monkeypatch, tmp_path):
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import get_step_types
    types = get_step_types()
    assert types == sorted(types)


# ── GET /api/step-types + POST steps end-to-end with a plugin registered ───────

def test_plugin_step_type_usable_via_api(client, headers, monkeypatch, tmp_path):
    _write_plugin(tmp_path, 'api_plugin.py', """
        from flowforge.steps.base import BaseStep, StepResult

        class ApiPluginStep(BaseStep):
            step_type = 'api_plugin_step'

            def run(self, context):
                return StepResult(success=True)
    """)
    monkeypatch.setenv('FLOWFORGE_PLUGIN_DIR', str(tmp_path))
    from flowforge.engine.loader import _load_plugins
    _load_plugins()

    resp = client.get('/api/step-types', headers=headers)
    assert resp.status_code == 200
    rows = {row['type']: row['plugin'] for row in resp.get_json()}
    assert rows.get('api_plugin_step') is True

    pipeline_resp = client.post('/api/pipelines', json={'name': '__plugin_step_test__', 'enabled': True}, headers=headers)
    assert pipeline_resp.status_code == 201
    pipeline_id = pipeline_resp.get_json()['id']
    try:
        step_resp = client.post(
            f'/api/pipelines/{pipeline_id}/steps',
            json={'name': 'plugin step', 'step_type': 'api_plugin_step'},
            headers=headers,
        )
        assert step_resp.status_code == 201
    finally:
        client.delete(f'/api/pipelines/{pipeline_id}', headers=headers)
