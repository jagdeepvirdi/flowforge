"""Unit tests for flowforge/registry.py's generic Registry primitive."""
import pytest

from flowforge.registry import IntegrationSpec, Registry


@pytest.fixture
def registry():
    return Registry('widgets')


class Foo:
    pass


class Bar:
    pass


# ─── register / get ───────────────────────────────────────────────────────────

def test_register_direct_call_returns_cls(registry):
    result = registry.register('foo', Foo)
    assert result is Foo
    assert registry.get('foo') is Foo


def test_register_as_decorator(registry):
    @registry.register('foo', display_name='Foo Widget')
    class Decorated:
        pass

    assert registry.get('foo') is Decorated


def test_register_decorator_preserves_class_identity(registry):
    @registry.register('foo')
    class Decorated:
        pass

    assert issubclass(Decorated, object)


def test_get_unknown_key_raises_keyerror(registry):
    with pytest.raises(KeyError):
        registry.get('missing')


def test_register_duplicate_key_raises(registry):
    registry.register('foo', Foo)
    with pytest.raises(ValueError):
        registry.register('foo', Bar)


# ─── list ──────────────────────────────────────────────────────────────────────

def test_list_returns_sorted_keys(registry):
    registry.register('zeta', Foo)
    registry.register('alpha', Bar)
    assert registry.list() == ['alpha', 'zeta']


def test_list_empty_registry(registry):
    assert registry.list() == []


# ─── metadata ──────────────────────────────────────────────────────────────────

def test_metadata_returns_kwargs(registry):
    registry.register('foo', Foo, display_name='Foo Widget', tier='free')
    assert registry.metadata('foo') == {'display_name': 'Foo Widget', 'tier': 'free'}


def test_metadata_defaults_to_empty_dict(registry):
    registry.register('foo', Foo)
    assert registry.metadata('foo') == {}


def test_metadata_unknown_key_raises_keyerror(registry):
    with pytest.raises(KeyError):
        registry.metadata('missing')


# ─── dunder helpers ────────────────────────────────────────────────────────────

def test_contains(registry):
    registry.register('foo', Foo)
    assert 'foo' in registry
    assert 'missing' not in registry


def test_len(registry):
    assert len(registry) == 0
    registry.register('foo', Foo)
    registry.register('bar', Bar)
    assert len(registry) == 2


# ─── isolation across Registry instances ──────────────────────────────────────

def test_categories_are_independent():
    steps = Registry('steps')
    connections = Registry('connections')
    steps.register('foo', Foo)
    assert 'foo' not in connections
    assert connections.list() == []


def test_reset_for_tests_clears_state(registry):
    registry.register('foo', Foo)
    registry._reset_for_tests()
    assert registry.list() == []
    assert 'foo' not in registry


# ─── IntegrationSpec / register_spec / spec() ─────────────────────────────────

def test_integration_spec_defaults():
    spec = IntegrationSpec(key='postgresql', display_name='PostgreSQL')
    assert spec.description == ''
    assert spec.requires is None
    assert spec.config_schema is None
    assert spec.tier is None


def test_integration_spec_is_frozen():
    spec = IntegrationSpec(key='postgresql', display_name='PostgreSQL')
    with pytest.raises(Exception):
        spec.tier = 'paid'


def test_register_spec_direct_call_returns_cls(registry):
    spec = IntegrationSpec(key='foo', display_name='Foo Widget', requires='foo-extra')
    result = registry.register_spec(spec, Foo)
    assert result is Foo
    assert registry.get('foo') is Foo


def test_register_spec_as_decorator(registry):
    spec = IntegrationSpec(key='foo', display_name='Foo Widget')

    @registry.register_spec(spec)
    class Decorated:
        pass

    assert registry.get('foo') is Decorated


def test_register_spec_stores_metadata(registry):
    spec = IntegrationSpec(
        key='oracle', display_name='Oracle', description='Oracle DB', requires='oracle',
        config_schema={'host': 'string'}, tier='paid',
    )
    registry.register_spec(spec, Foo)
    assert registry.metadata('oracle') == {
        'key': 'oracle', 'display_name': 'Oracle', 'description': 'Oracle DB',
        'requires': 'oracle', 'config_schema': {'host': 'string'}, 'tier': 'paid',
    }


def test_spec_roundtrips_through_registry(registry):
    original = IntegrationSpec(key='foo', display_name='Foo Widget', tier='free')
    registry.register_spec(original, Foo)
    assert registry.spec('foo') == original


def test_register_spec_duplicate_key_raises(registry):
    registry.register_spec(IntegrationSpec(key='foo', display_name='Foo'), Foo)
    with pytest.raises(ValueError):
        registry.register_spec(IntegrationSpec(key='foo', display_name='Foo Again'), Bar)


def test_spec_on_plain_register_missing_fields_raises(registry):
    # Registered via loose kwargs, not register_spec() — metadata doesn't match
    # IntegrationSpec's required fields, so reconstructing one should fail loudly.
    registry.register('foo', Foo, display_name='Foo Widget')
    with pytest.raises(TypeError):
        registry.spec('foo')


# ─── unregister ────────────────────────────────────────────────────────────────

def test_unregister_removes_class_and_metadata(registry):
    registry.register('foo', Foo, display_name='Foo Widget')
    registry.unregister('foo')
    assert 'foo' not in registry
    with pytest.raises(KeyError):
        registry.get('foo')
    with pytest.raises(KeyError):
        registry.metadata('foo')


def test_unregister_unknown_key_raises(registry):
    with pytest.raises(KeyError):
        registry.unregister('missing')


def test_unregister_then_reregister(registry):
    registry.register('foo', Foo)
    registry.unregister('foo')
    registry.register('foo', Bar)
    assert registry.get('foo') is Bar
