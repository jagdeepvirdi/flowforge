"""ai_analyze step — legacy shell.

The AI analysis logic moved out of Core to the external Brain service. The type stays
registered so saved pipelines and run history still load; running it fails loudly rather than
injecting canned output into emails and reports (docs/BRAIN_DECOUPLING_PLAN.md §3).
"""
from typing import Any

from flowforge.steps.base import BaseStep, StepResult


class AiAnalyzeStep(BaseStep):
    step_type = 'ai_analyze'

    def run(self, context: dict[str, Any]) -> StepResult:
        # TODO: Wire this to the new external Brain microservice API
        return StepResult(
            success=False,
            error='ai_analyze requires the Brain service (FLOWFORGE_BRAIN_URL) — not attached',
        )
