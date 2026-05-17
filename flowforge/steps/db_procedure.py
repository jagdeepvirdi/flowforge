import logging
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class DbProcedureStep(BaseStep):
    """Calls a stored procedure or package on a configured database connection."""

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        procedure = self.config['procedure']
        raw_params = self.config.get('params', {})
        params = {k: render(str(v), context) for k, v in raw_params.items()}

        conn = self._get_connection()
        try:
            with conn:
                conn.execute_procedure(procedure, params)
            logger.info("Procedure '%s' completed (%d params)", procedure, len(params))
            return StepResult(success=True, logs=f"Called {procedure} ({len(params)} params)")
        except Exception as e:
            logger.error("Procedure '%s' failed: %s", procedure, e)
            return StepResult(success=False, error=str(e))

    def _get_connection(self):
        connection_id = self.config.get('connection_id')
        if connection_id:
            from flowforge.connections.factory import get_connection
            return get_connection(connection_id)
        # Fallback: env vars (used when running outside a Flask app context)
        import os
        from flowforge.connections.postgres import PostgreSQLConnection
        return PostgreSQLConnection(
            host=os.environ.get('DB_HOST', ''),
            database=os.environ.get('DB_NAME', ''),
            user=os.environ.get('DB_USER', ''),
            password=os.environ.get('DB_PASSWORD', ''),
        )
