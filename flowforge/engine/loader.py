"""Load a pipeline definition from the database into executable step objects.

Also owns the step-type registry (built-in step classes plus any community
plugin step classes loaded from FLOWFORGE_PLUGIN_DIR — see _load_plugins).
"""
import importlib
import inspect
import logging
import os
import sys
from pathlib import Path

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


def _load_plugins() -> None:
    """Scan FLOWFORGE_PLUGIN_DIR (default ./plugins) for *.py files and register any
    BaseStep subclass they define, keyed by its `step_type` class attribute.

    Runs at most once per process. A plugin file that fails to import, or that
    defines no usable BaseStep subclass, is logged and skipped — it never blocks
    startup or other plugins. See docs/plugins.md for the authoring contract.
    """
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED:
        return
    _PLUGINS_LOADED = True

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
            logger.exception("Failed to load plugin step file: %s", py_file)
            continue

        registered = 0
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is BaseStep or not issubclass(obj, BaseStep) or obj.__module__ != module_name:
                continue
            step_type = getattr(obj, 'step_type', '') or ''
            if not step_type:
                logger.warning("Plugin class %s in %s has no step_type set — skipped", obj.__name__, py_file.name)
                continue
            if step_type in _STEP_CLASSES:
                logger.warning(
                    "Plugin step_type '%s' from %s conflicts with an existing step type — skipped",
                    step_type, py_file.name,
                )
                continue
            _STEP_CLASSES[step_type] = obj
            registered += 1
            logger.info("Registered plugin step type '%s' from %s", step_type, py_file.name)
        if not registered:
            logger.warning("Plugin file %s defined no usable BaseStep subclass — nothing registered", py_file.name)


def get_step_types() -> list[str]:
    """Return every registered step_type (built-ins + plugins), loading plugins first."""
    _load_plugins()
    return sorted(_STEP_CLASSES)


def is_plugin_step_type(step_type: str) -> bool:
    return step_type in _STEP_CLASSES and step_type not in _BUILTIN_STEP_TYPES


def _reset_plugin_state_for_tests() -> None:
    """Test-only: drop plugin-registered types and allow _load_plugins to run again."""
    global _PLUGINS_LOADED
    for step_type in list(_STEP_CLASSES):
        if step_type not in _BUILTIN_STEP_TYPES:
            del _STEP_CLASSES[step_type]
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
        steps.append(cls(name=step_row.name, config=config))
        logger.debug("Loaded step %d: %s (%s)", step_row.step_order, step_row.name, step_row.step_type)

    logger.info("Loaded pipeline '%s': %d steps", pipeline.name, len(steps))
    return steps, pipeline_vars, secret_keys
