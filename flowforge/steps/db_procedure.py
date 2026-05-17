import logging
import os
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class DbProcedureStep(BaseStep):
    """Calls a stored procedure or package on a configured database connection."""

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.connections.postgres import PostgreSQLConnection
        from flowforge.engine.context import render

        procedure = self.config['procedure']
        raw_params = self.config.get('params', {})
        params = {k: render(str(v), context) for k, v in raw_params.items()}

        # Phase 1 will load connection config from DB via connection_id.
        # Until then, fall back to env vars.
        conn = PostgreSQLConnection(
            host=os.environ.get('DB_HOST', ''),
            database=os.environ.get('DB_NAME', ''),
            user=os.environ.get('DB_USER', ''),
            password=os.environ.get('DB_PASSWORD', ''),
        )
        try:
            with conn:
                conn.execute_procedure(procedure, params)
            logger.info("Procedure '%s' completed", procedure)
            return StepResult(success=True, logs=f"Called {procedure} ({len(params)} params)")
        except Exception as e:
            logger.error("Procedure '%s' failed: %s", procedure, e)
            return StepResult(success=False, error=str(e))
