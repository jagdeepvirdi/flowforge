"""Load a pipeline definition from the database into executable step objects.

Also owns the step-type registry (built-in step classes plus any community
plugin step classes loaded from FLOWFORGE_PLUGIN_DIR or a pip-installed
"flowforge.plugins" entry point — see _load_plugins) and the generic plugin
scanner (_PluginCategory / _register_plugin_class) that a single plugin file
or entry point is checked against, so it may define a step, a connection, or
an email provider — see docs/TASKS.md Phase 13.3.
"""
import importlib
import importlib.metadata
import importlib.util
import inspect
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from flowforge.crypto import decrypt_value
from flowforge.db.models import Pipeline, db
from flowforge.steps.base import BaseStep

logger = logging.getLogger(__name__)

# Built-in step types map to a dotted class path (lazily imported on first use).
# Plugin step types (registered by _load_plugins) map directly to the already-
# imported class object instead of a dotted path.
_STEP_CLASSES: dict[str, str | type[BaseStep]] = {
    'db_procedure':    'flowforge.steps.db_procedure.DbProcedureStep',
    'db_query':        'flowforge.steps.db_query.DbQueryStep',
    'report':          'flowforge.steps.report.ReportStep',
    'email':           'flowforge.steps.email_step.EmailStep',
    'drive_upload':    'flowforge.steps.drive_upload.DriveUploadStep',
    'onedrive_upload': 'flowforge.steps.onedrive_upload.OneDriveUploadStep',
    'data_load':       'flowforge.steps.data_load.DataLoadStep',
    'bulk_load':       'flowforge.steps.bulk_load.BulkLoadStep',
    'ai_analyze':      'flowforge.steps.ai_analyze.AiAnalyzeStep',
    'sftp_transfer':   'flowforge.steps.sftp_transfer.SftpTransferStep',
    'ssh_command':      'flowforge.steps.ssh_command.SshCommandStep',
    'db_health_check':  'flowforge.steps.db_health_check.DbHealthCheckStep',
    'data_report':      'flowforge.steps.script_report.ScriptReportStep',
    'ssh_health_check': 'flowforge.steps.ssh_health_check.SshHealthCheckStep',
    'notification':     'flowforge.steps.notification.NotificationStep',
    's3_upload':          'flowforge.steps.s3_upload.S3UploadStep',
    'azure_blob_upload':  'flowforge.steps.azure_blob_upload.AzureBlobUploadStep',
}

_BUILTIN_STEP_TYPES = frozenset(_STEP_CLASSES)
_PLUGINS_LOADED = False


def _step_contains(key: str) -> bool:
    return key in _STEP_CLASSES


def _step_register(key: str, cls: type) -> None:
    _STEP_CLASSES[key] = cls


@dataclass
class _PluginCategory:
    """One pluggable category the plugin scanner checks a class against.

    `contains`/`register` abstract over each category's own storage — steps
    use the module-level `_STEP_CLASSES` dict directly; connections/email
    providers use their `Registry` instances (flowforge/registry.py) — so the
    scanner below doesn't need to know how each category stores things.
    """
    label: str            # for log messages, e.g. "step", "connection"
    base_class: type
    key_attr: str          # class attribute holding the registration key, e.g. "step_type"
    contains: Callable[[str], bool]
    register: Callable[[str, type], None]


def _plugin_categories() -> list[_PluginCategory]:
    """Built lazily (not at import time) to avoid a hard import-order dependency
    between this module and the connections/email_providers factory modules."""
    from flowforge.connections.base import BaseConnection
    from flowforge.connections.factory import connections_registry
    from flowforge.email_providers.base import EmailProvider
    from flowforge.email_providers.factory import providers_registry

    return [
        _PluginCategory('step', BaseStep, 'step_type', _step_contains, _step_register),
        _PluginCategory('connection', BaseConnection, 'db_type',
                         connections_registry.__contains__, connections_registry.register),
        _PluginCategory('email provider', EmailProvider, 'provider_type',
                         providers_registry.__contains__, providers_registry.register),
    ]


def _register_plugin_class(obj: type, categories: list[_PluginCategory], source: str) -> bool:
    """Try to register `obj` against whichever category's base class it subclasses.

    Returns True if registered. A class belongs to at most one category — the
    base classes (BaseStep, BaseConnection, EmailProvider) are unrelated
    hierarchies, so the first category that matches `issubclass` is decisive:
    if its `key_attr` is missing or already registered, nothing else would
    have matched either, so we log and stop rather than trying the rest.
    """
    for category in categories:
        if obj is category.base_class or not issubclass(obj, category.base_class):
            continue
        key = getattr(obj, category.key_attr, '') or ''
        if not key:
            logger.warning(
                "Plugin %s class %s from %s has no %s set — skipped",
                category.label, obj.__name__, source, category.key_attr,
            )
            return False
        if category.contains(key):
            logger.warning(
                "Plugin %s '%s' from %s conflicts with an existing one — skipped",
                category.label, key, source,
            )
            return False
        category.register(key, obj)
        logger.info("Registered plugin %s '%s' from %s", category.label, key, source)
        return True
    return False


def _load_directory_plugins(categories: list[_PluginCategory]) -> None:
    """Scan FLOWFORGE_PLUGIN_DIR (default ./plugins) for *.py files and register any
    recognized plugin class they define (see _plugin_categories), keyed by that
    category's key attribute (e.g. `step_type`, `db_type`, `provider_type`).

    A plugin file that fails to import, or that defines no usable plugin class,
    is logged and skipped — it never blocks startup or other plugins. See
    docs/plugins.md for the authoring contract.
    """
    plugin_dir = Path(os.environ.get('FLOWFORGE_PLUGIN_DIR', './plugins'))
    if not plugin_dir.is_dir():
        return

    for py_file in sorted(plugin_dir.glob('*.py')):
        if py_file.stem.startswith('_'):
            continue
        module_name = f'flowforge_plugin_{py_file.stem}'
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            logger.exception("Failed to load plugin file: %s", py_file)
            continue

        registered = 0
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module_name:
                continue
            if _register_plugin_class(obj, categories, source=py_file.name):
                registered += 1
        if not registered:
            logger.warning("Plugin file %s defined no usable plugin class — nothing registered", py_file.name)


def _load_entry_point_plugins(categories: list[_PluginCategory]) -> None:
    """Load plugins registered by a pip-installed package via the
    `flowforge.plugins` entry-point group, e.g. in pyproject.toml:

        [project.entry-points."flowforge.plugins"]
        my_plugin = "my_package.plugin:MyStep"

    This is what makes a plugin distributable/pip-installable, rather than
    only usable by dropping a file into FLOWFORGE_PLUGIN_DIR.
    """
    try:
        entry_points = importlib.metadata.entry_points(group='flowforge.plugins')
    except Exception:
        logger.exception("Failed to enumerate 'flowforge.plugins' entry points")
        return

    for ep in entry_points:
        source = f"entry point '{ep.name}'"
        try:
            obj = ep.load()
        except Exception:
            logger.exception("Failed to load plugin %s", source)
            continue
        if not inspect.isclass(obj):
            logger.warning("Plugin %s does not resolve to a class — skipped", source)
            continue
        _register_plugin_class(obj, categories, source=source)


def _load_plugins() -> None:
    """Load plugins from both FLOWFORGE_PLUGIN_DIR and installed entry points.

    Runs at most once per process.
    """
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED:
        return
    _PLUGINS_LOADED = True

    categories = _plugin_categories()
    _load_directory_plugins(categories)
    _load_entry_point_plugins(categories)


def get_step_types() -> list[str]:
    """Return every registered step_type (built-ins + plugins), loading plugins first."""
    _load_plugins()
    return sorted(_STEP_CLASSES)


def is_plugin_step_type(step_type: str) -> bool:
    return step_type in _STEP_CLASSES and step_type not in _BUILTIN_STEP_TYPES


def _reset_plugin_state_for_tests() -> None:
    """Test-only: drop plugin-registered types (steps, connections, email
    providers) and allow _load_plugins to run again."""
    global _PLUGINS_LOADED
    for step_type in list(_STEP_CLASSES):
        if step_type not in _BUILTIN_STEP_TYPES:
            del _STEP_CLASSES[step_type]

    from flowforge.connections.factory import BUILTIN_DB_TYPES, connections_registry
    from flowforge.email_providers.factory import BUILTIN_PROVIDER_TYPES, providers_registry
    for db_type in connections_registry.list():
        if db_type not in BUILTIN_DB_TYPES:
            connections_registry.unregister(db_type)
    for provider_type in providers_registry.list():
        if provider_type not in BUILTIN_PROVIDER_TYPES:
            providers_registry.unregister(provider_type)

    _PLUGINS_LOADED = False


def _import_step_class(cls_entry: str | type[BaseStep]):
    if isinstance(cls_entry, type):
        return cls_entry
    module_path, class_name = cls_entry.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def load_pipeline(pipeline_id: str) -> tuple[list[BaseStep], dict[str, str], set[str]]:
    """
    Load a pipeline from the database.

    Returns:
        steps         — ordered list of BaseStep instances ready to execute
        pipeline_vars — dict of pipeline-level variables (keys → values)
        secret_keys   — set of var_key names that are secret (for log masking)
    """
    _load_plugins()

    pipeline: Pipeline | None = db.session.get(Pipeline, pipeline_id)
    if not pipeline:
        raise ValueError(f"Pipeline not found: {pipeline_id}")
    if not pipeline.enabled:
        raise ValueError(f"Pipeline is disabled: {pipeline.name}")

    pipeline_vars: dict[str, str] = {}
    pipeline_vars['pipeline_send_only_on_failure'] = 'true' if pipeline.send_only_on_failure else 'false'
    secret_keys: set[str] = set()
    for v in pipeline.variables:
        try:
            value = decrypt_value(v.var_value) if v.is_secret else v.var_value
        except Exception:
            # Tolerate unencrypted legacy values (stored before encryption was added)
            value = v.var_value
        pipeline_vars[v.var_key] = value
        if v.is_secret:
            secret_keys.add(v.var_key)

    steps: list[BaseStep] = []
    for step_row in pipeline.steps:
        if not step_row.enabled:
            logger.info("Skipping disabled step: %s", step_row.name)
            continue

        cls_entry = _STEP_CLASSES.get(step_row.step_type)
        if not cls_entry:
            raise ValueError(f"Unknown step type: {step_row.step_type}")

        cls = _import_step_class(cls_entry)
        config = dict(step_row.config)
        config['on_error']        = step_row.on_error
        config['parallel_group']  = step_row.parallel_group
        config['_db_step_order']  = step_row.step_order
        config['_db_step_id']     = step_row.id
        steps.append(cls(name=step_row.name, config=config))
        logger.debug("Loaded step %d: %s (%s)", step_row.step_order, step_row.name, step_row.step_type)

    logger.info("Loaded pipeline '%s': %d steps", pipeline.name, len(steps))
    return steps, pipeline_vars, secret_keys
