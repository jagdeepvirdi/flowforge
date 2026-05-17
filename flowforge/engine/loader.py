"""Load a pipeline definition from the database into executable step objects."""
import logging

from flowforge.db.models import Pipeline, db
from flowforge.steps.base import BaseStep

logger = logging.getLogger(__name__)

_STEP_CLASSES: dict[str, str] = {
    'db_procedure': 'flowforge.steps.db_procedure.DbProcedureStep',
    'db_query':     'flowforge.steps.db_query.DbQueryStep',
    'report':       'flowforge.steps.report.ReportStep',
    'email':        'flowforge.steps.email_step.EmailStep',
    'drive_upload': 'flowforge.steps.drive_upload.DriveUploadStep',
}


def _import_step_class(dotted_path: str):
    module_path, class_name = dotted_path.rsplit('.', 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def load_pipeline(pipeline_id: str) -> tuple[list[BaseStep], dict[str, str]]:
    """
    Load a pipeline from the database.

    Returns:
        steps        — ordered list of BaseStep instances ready to execute
        pipeline_vars — dict of pipeline-level variables (keys → values)
    """
    pipeline: Pipeline | None = db.session.get(Pipeline, pipeline_id)
    if not pipeline:
        raise ValueError(f"Pipeline not found: {pipeline_id}")
    if not pipeline.enabled:
        raise ValueError(f"Pipeline is disabled: {pipeline.name}")

    pipeline_vars: dict[str, str] = {
        v.var_key: v.var_value
        for v in pipeline.variables
        if not v.is_secret
    }
    # Secret vars ARE passed to the runner context (they're used internally by steps),
    # but the API serialisation masks them from clients.
    for v in pipeline.variables:
        if v.is_secret:
            pipeline_vars[v.var_key] = v.var_value

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
    return steps, pipeline_vars
