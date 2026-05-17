import logging
from dataclasses import dataclass, field
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    success: bool
    pipeline_name: str
    steps_run: int = 0
    steps_failed: int = 0
    step_results: dict[str, StepResult] = field(default_factory=dict)
    error: str = ''


def run_pipeline(
    pipeline_name: str,
    steps: list[BaseStep],
    pipeline_vars: dict[str, str] | None = None,
    triggered_by: str = 'api',
) -> PipelineResult:
    """Execute an ordered list of steps, threading context between them."""
    from flowforge.engine.context import build

    context = build(pipeline_name, pipeline_vars=pipeline_vars)
    context['triggered_by'] = triggered_by

    result = PipelineResult(success=True, pipeline_name=pipeline_name)

    for step in steps:
        logger.info("[%s] Starting step: %s", pipeline_name, step.name)
        try:
            step_result = step.run(context)
        except Exception as e:
            logger.error("[%s] Step '%s' raised uncaught exception: %s", pipeline_name, step.name, e)
            step_result = StepResult(success=False, error=str(e))

        result.step_results[step.name] = step_result
        result.steps_run += 1

        # Expose this step's outputs to downstream steps via {{ steps.name.* }}
        context['steps'][step.name] = {
            'output_path': step_result.output_path,
            'drive_url': step_result.drive_url,
            'rows_affected': step_result.rows_affected,
        }

        if not step_result.success:
            result.steps_failed += 1
            if step.on_error == 'stop':
                logger.error(
                    "[%s] Step '%s' failed (on_error=stop). Error: %s",
                    pipeline_name, step.name, step_result.error,
                )
                result.success = False
                result.error = step_result.error
                break
            logger.warning(
                "[%s] Step '%s' failed (on_error=continue). Error: %s",
                pipeline_name, step.name, step_result.error,
            )

    if result.success:
        logger.info("[%s] Pipeline completed (%d steps)", pipeline_name, result.steps_run)
    else:
        logger.error("[%s] Pipeline failed after %d/%d steps", pipeline_name, result.steps_run, len(steps))

    return result
