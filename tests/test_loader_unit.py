"""Unit tests for flowforge/engine/loader.py.

Uses mocked db.session — no live database required.
Covers: _import_step_class, load_pipeline (not-found, disabled, variables,
secret decryption, disabled-step skip, unknown step type, on_error propagation).
"""
from unittest.mock import MagicMock, patch, call
import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_pipeline(enabled=True, name='Test Pipeline', variables=None, steps=None,
                   send_only_on_failure=False):
    p = MagicMock()
    p.enabled = enabled
    p.name = name
    p.variables = variables or []
    p.steps = steps or []
    p.send_only_on_failure = send_only_on_failure
    return p


def _make_var(key, value, is_secret=False):
    v = MagicMock()
    v.var_key = key
    v.var_value = value
    v.is_secret = is_secret
    return v


def _make_step_row(name='step1', step_type='bulk_load', step_order=1,
                   enabled=True, config=None, on_error='stop'):
    s = MagicMock()
    s.name = name
    s.step_type = step_type
    s.step_order = step_order
    s.enabled = enabled
    s.config = config if config is not None else {}
    s.on_error = on_error
    return s


# ─── _import_step_class ───────────────────────────────────────────────────────

def test_import_step_class_returns_class():
    from flowforge.engine.loader import _import_step_class
    from flowforge.steps.bulk_load import BulkLoadStep
    cls = _import_step_class('flowforge.steps.bulk_load.BulkLoadStep')
    assert cls is BulkLoadStep


def test_import_step_class_returns_correct_type():
    from flowforge.engine.loader import _import_step_class
    cls = _import_step_class('flowforge.steps.bulk_load.BulkLoadStep')
    assert callable(cls)


def test_import_step_class_sftp():
    from flowforge.engine.loader import _import_step_class
    from flowforge.steps.sftp_transfer import SftpTransferStep
    cls = _import_step_class('flowforge.steps.sftp_transfer.SftpTransferStep')
    assert cls is SftpTransferStep


def test_import_step_class_bad_class_name_raises():
    from flowforge.engine.loader import _import_step_class
    with pytest.raises(AttributeError):
        _import_step_class('flowforge.steps.bulk_load.NonExistentClass')


def test_import_step_class_bad_module_raises():
    from flowforge.engine.loader import _import_step_class
    with pytest.raises(ModuleNotFoundError):
        _import_step_class('flowforge.steps.nonexistent_module.SomeClass')


# ─── load_pipeline — error paths ─────────────────────────────────────────────

def test_load_pipeline_not_found_raises():
    from flowforge.engine.loader import load_pipeline
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = None
        with pytest.raises(ValueError, match='Pipeline not found'):
            load_pipeline('nonexistent-uuid')


def test_load_pipeline_disabled_raises():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(enabled=False)
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        with pytest.raises(ValueError, match='disabled'):
            load_pipeline('some-uuid')


# ─── load_pipeline — non-secret variables ────────────────────────────────────

def test_load_pipeline_non_secret_var_in_pipeline_vars():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(
        variables=[_make_var('MY_KEY', 'my_value', is_secret=False)],
        steps=[],
    )
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        steps, pipeline_vars, secret_keys = load_pipeline('uuid')
    assert pipeline_vars['MY_KEY'] == 'my_value'
    assert 'MY_KEY' not in secret_keys


def test_load_pipeline_multiple_vars():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(
        variables=[
            _make_var('K1', 'v1'),
            _make_var('K2', 'v2'),
            _make_var('K3', 'v3'),
        ],
        steps=[],
    )
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        _, pipeline_vars, _ = load_pipeline('uuid')
    assert pipeline_vars == {'K1': 'v1', 'K2': 'v2', 'K3': 'v3', 'pipeline_send_only_on_failure': 'false'}


# ─── load_pipeline — secret variables ────────────────────────────────────────

def test_load_pipeline_secret_var_is_decrypted():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(
        variables=[_make_var('DB_PASS', 'encrypted_blob', is_secret=True)],
        steps=[],
    )
    with patch('flowforge.engine.loader.db') as mock_db, \
         patch('flowforge.engine.loader.decrypt_value', return_value='cleartext_pass') as mock_dec:
        mock_db.session.get.return_value = pipeline
        _, pipeline_vars, _ = load_pipeline('uuid')
    mock_dec.assert_called_once_with('encrypted_blob')
    assert pipeline_vars['DB_PASS'] == 'cleartext_pass'


def test_load_pipeline_secret_var_added_to_secret_keys():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(
        variables=[_make_var('API_KEY', 'encrypted', is_secret=True)],
        steps=[],
    )
    with patch('flowforge.engine.loader.db') as mock_db, \
         patch('flowforge.engine.loader.decrypt_value', return_value='decoded'):
        mock_db.session.get.return_value = pipeline
        _, _, secret_keys = load_pipeline('uuid')
    assert 'API_KEY' in secret_keys


def test_load_pipeline_non_secret_not_in_secret_keys():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(
        variables=[_make_var('PLAIN_KEY', 'value', is_secret=False)],
        steps=[],
    )
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        _, _, secret_keys = load_pipeline('uuid')
    assert 'PLAIN_KEY' not in secret_keys


def test_load_pipeline_decrypt_failure_falls_back_to_raw_value():
    """If decrypt_value raises, the raw value is used (legacy tolerance)."""
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(
        variables=[_make_var('OLD_KEY', 'not_encrypted', is_secret=True)],
        steps=[],
    )
    with patch('flowforge.engine.loader.db') as mock_db, \
         patch('flowforge.engine.loader.decrypt_value', side_effect=Exception('bad token')):
        mock_db.session.get.return_value = pipeline
        _, pipeline_vars, _ = load_pipeline('uuid')
    assert pipeline_vars['OLD_KEY'] == 'not_encrypted'


# ─── load_pipeline — step loading ────────────────────────────────────────────

def test_load_pipeline_disabled_step_skipped():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(steps=[
        _make_step_row('s1', 'bulk_load', 1, enabled=True),
        _make_step_row('s2', 'bulk_load', 2, enabled=False),
    ])
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        steps, _, _ = load_pipeline('uuid')
    assert len(steps) == 1
    assert steps[0].name == 's1'


def test_load_pipeline_unknown_step_type_raises():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(steps=[
        _make_step_row('bad', 'nonexistent_step_type', 1, enabled=True),
    ])
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        with pytest.raises(ValueError, match='Unknown step type'):
            load_pipeline('uuid')


def test_load_pipeline_returns_steps_in_order():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(steps=[
        _make_step_row('first',  'bulk_load', 1),
        _make_step_row('second', 'bulk_load', 2),
        _make_step_row('third',  'bulk_load', 3),
    ])
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        steps, _, _ = load_pipeline('uuid')
    assert [s.name for s in steps] == ['first', 'second', 'third']


def test_load_pipeline_step_on_error_set_from_row():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(steps=[
        _make_step_row('s1', 'bulk_load', 1, on_error='continue'),
    ])
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        steps, _, _ = load_pipeline('uuid')
    assert steps[0].on_error == 'continue'


def test_load_pipeline_step_config_includes_on_error():
    """config dict passed to the step constructor must contain 'on_error'."""
    from flowforge.engine.loader import load_pipeline
    from flowforge.steps.bulk_load import BulkLoadStep
    pipeline = _make_pipeline(steps=[
        _make_step_row('s1', 'bulk_load', 1, config={'connection_id': 'x'}, on_error='continue'),
    ])
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        steps, _, _ = load_pipeline('uuid')
    assert isinstance(steps[0], BulkLoadStep)
    assert steps[0].config['on_error'] == 'continue'


def test_load_pipeline_empty_steps_returns_empty_list():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(steps=[])
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        steps, _, _ = load_pipeline('uuid')
    assert steps == []


def test_load_pipeline_all_disabled_steps_returns_empty():
    from flowforge.engine.loader import load_pipeline
    pipeline = _make_pipeline(steps=[
        _make_step_row('s1', 'bulk_load', 1, enabled=False),
        _make_step_row('s2', 'bulk_load', 2, enabled=False),
    ])
    with patch('flowforge.engine.loader.db') as mock_db:
        mock_db.session.get.return_value = pipeline
        steps, _, _ = load_pipeline('uuid')
    assert steps == []


def test_load_pipeline_known_step_types_all_importable():
    """Every registered step type can be resolved to a real class."""
    from flowforge.engine.loader import _STEP_CLASSES, _import_step_class
    for step_type, dotted_path in _STEP_CLASSES.items():
        cls = _import_step_class(dotted_path)
        assert callable(cls), f'{step_type} -> {dotted_path} did not resolve to a callable'


# ─── _STEP_CLASSES registry ───────────────────────────────────────────────────

def test_all_expected_step_types_registered():
    from flowforge.engine.loader import _STEP_CLASSES
    expected = {'db_procedure', 'db_query', 'report', 'email', 'drive_upload',
                'onedrive_upload', 'data_load', 'bulk_load', 'ai_analyze', 'sftp_transfer'}
    assert expected.issubset(_STEP_CLASSES.keys())
