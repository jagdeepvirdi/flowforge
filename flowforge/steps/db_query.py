import logging
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)

_VALID_MODES = {'replace', 'append', 'truncate_insert'}


class DbQueryStep(BaseStep):
    """Executes a SQL query and optionally writes results to an output table."""

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        sql = render(self.config['query'], context)
        output_table = self.config.get('output_table', '')
        mode = self.config.get('mode', 'replace')

        if output_table and mode not in _VALID_MODES:
            return StepResult(success=False, error=f"Invalid mode '{mode}'. Must be one of: {', '.join(_VALID_MODES)}")

        conn = self._get_connection()
        try:
            with conn:
                rows = conn.execute_query(sql)

                if output_table and rows:
                    if mode in ('replace', 'truncate_insert'):
                        # Table name is from trusted config (not user input), so
                        # direct interpolation here is acceptable.
                        conn.execute_write(f'TRUNCATE TABLE {output_table}')
                    placeholders = ', '.join(['%s'] * len(rows[0]))
                    insert_sql = f'INSERT INTO {output_table} VALUES ({placeholders})'
                    for row in rows:
                        conn.execute_write(insert_sql, tuple(row))

            logger.info("Query returned %d rows", len(rows))
            return StepResult(success=True, rows_affected=len(rows))
        except Exception as e:
            logger.error("DB query step failed: %s", e)
            return StepResult(success=False, error=str(e))

    def _get_connection(self):
        connection_id = self.config.get('connection_id')
        if connection_id:
            from flowforge.connections.factory import get_connection
            return get_connection(connection_id)
        import os
        from flowforge.connections.postgres import PostgreSQLConnection
        return PostgreSQLConnection(
            host=os.environ.get('DB_HOST', ''),
            database=os.environ.get('DB_NAME', ''),
            user=os.environ.get('DB_USER', ''),
            password=os.environ.get('DB_PASSWORD', ''),
        )
