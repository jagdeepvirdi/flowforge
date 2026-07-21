"""GET /api/registry/<category> and GET /api/registry — read-only introspection
over FlowForge's pluggable categories (steps, connections, email providers),
backed by the registries built in Phase 13 (flowforge/registry.py, plus
engine/loader.py's own step dispatch — steps were never migrated onto the
generic `Registry` class, see docs/TASKS.md Phase 13.3 for why).

Replaces frontend-hardcoded step/connection/provider-type arrays (ARCH-9) and
gives a single aggregate view of what's registered vs. actually installed
(ARCH-11). `entitled` is a hardcoded `True` stub — no entitlement/tier system
exists yet, so this endpoint is purely informational (the introspection seam,
not a gate).
"""
import importlib.util

from flask import Blueprint, jsonify

from flowforge.api.auth import require_auth

bp = Blueprint('registry', __name__)

# Maps an IntegrationSpec.requires pip-extra name to the module actually
# probed to answer "is it installed" — the extra name and the underlying
# importable package don't always match (e.g. extra "oracle" installs the
# "oracledb" package).
_EXTRA_TO_MODULE: dict[str, str] = {
    'oracle': 'oracledb',
    'mysql': 'pymysql',
    'mssql': 'pyodbc',
    'snowflake': 'snowflake.connector',
    'bigquery': 'google.cloud.bigquery',
    'ses': 'boto3',
    'sendgrid': 'requests',
    'mailgun': 'requests',
}


def _module_installed(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _is_installed(requires: str | None) -> bool:
    if not requires:
        return True
    return _module_installed(_EXTRA_TO_MODULE.get(requires, requires))


def _step_entries() -> list[dict]:
    from flowforge.engine.loader import get_step_types, is_plugin_step_type

    # Steps carry no `requires`/IntegrationSpec metadata yet (never migrated
    # onto the generic Registry) — every entry reports installed=True since a
    # step's class had to import successfully to be registered at all.
    return [
        {
            'key': t, 'display_name': t, 'description': '',
            'plugin': is_plugin_step_type(t), 'requires': None,
            'installed': True, 'tier': None,
        }
        for t in get_step_types()
    ]


def _registry_entries(registry, builtin_keys: frozenset) -> list[dict]:
    entries = []
    for key in registry.list():
        is_plugin = key not in builtin_keys
        if is_plugin:
            # Plugin classes are registered directly (no IntegrationSpec metadata) —
            # see engine/loader.py's _register_plugin_class.
            entry = {'key': key, 'display_name': key, 'description': '', 'requires': None, 'tier': None}
        else:
            spec = registry.spec(key)
            entry = {
                'key': spec.key, 'display_name': spec.display_name, 'description': spec.description,
                'requires': spec.requires, 'tier': spec.tier,
            }
        entry['plugin'] = is_plugin
        entry['installed'] = _is_installed(entry['requires'])
        entries.append(entry)
    return entries


def _connection_entries() -> list[dict]:
    from flowforge.connections.factory import BUILTIN_DB_TYPES, connections_registry
    return _registry_entries(connections_registry, BUILTIN_DB_TYPES)


def _provider_entries() -> list[dict]:
    from flowforge.email_providers.factory import BUILTIN_PROVIDER_TYPES, providers_registry
    return _registry_entries(providers_registry, BUILTIN_PROVIDER_TYPES)


_ENTRY_FNS = {
    'steps': _step_entries,
    'connections': _connection_entries,
    'email_providers': _provider_entries,
}


@bp.get('/registry/<category>')
@require_auth
def get_category_registry(category):
    fn = _ENTRY_FNS.get(category)
    if fn is None:
        return jsonify({
            'error': f"Unknown registry category: '{category}'. Must be one of: {', '.join(sorted(_ENTRY_FNS))}"
        }), 404
    return jsonify(fn())


@bp.get('/registry')
@require_auth
def get_aggregate_registry():
    entries = []
    for category, fn in _ENTRY_FNS.items():
        for entry in fn():
            entries.append({'category': category, **entry, 'entitled': True})
    return jsonify(entries)
