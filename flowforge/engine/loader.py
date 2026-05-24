"""Load a pipeline definition from the database into executable step objects."""
import logging

from flowforge.crypto import decrypt_value
from flowforge.db.models import Pipeline, db
from flowforge.steps.base import BaseStep

logger = logging.getLogger(__name__)

_STEP_CLASSES: dict[str, str] = {
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
}


def _import_step_class(dotted_path: str):
    module_path, class_name = dotted_path.rsplit('.', 1)
    import importlib
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
    pipeline: Pipeline | None = db.session.get(Pipeline, pipeline_id)
    if not pipeline:
        raise ValueError(f"Pipeline not found: {pipeline_id}")
    if not pipeline.enabled:
        raise ValueError(f"Pipeline is disabled: {pipeline.name}")

    pipeline_vars: dict[str, str] = {}
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

        cls_path = _STEP_CLASSES.get(step_row.step_type)
        if not cls_path:
            raise ValueError(f"Unknown step type: {step_row.step_type}")

        cls = _import_step_class(cls_path)
        config = dict(step_row.config)
        config['on_error'] = step_row.on_error
        steps.append(cls(name=step_row.name, config=config))
        logger.debug("Loaded step %d: %s (%s)", step_row.step_order, step_row.name, step_row.step_type)

    logger.info("Loaded pipeline '%s': %d steps", pipeline.name, len(steps))
    return steps, pipeline_vars, secret_keys
