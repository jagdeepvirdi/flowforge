import logging
import os
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class DbQueryStep(BaseStep):
    """Executes a SQL query and optionally writes results to an output table."""

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.connections.postgres import PostgreSQLConnection
        from flowforge.engine.context import render

        sql = render(self.config['query'], context)
        output_table = self.config.get('output_table', '')
        mode = self.config.get('mode', 'replace')

        conn = PostgreSQLConnection(
            host=os.environ.get('DB_HOST', ''),
            database=os.environ.get('DB_NAME', ''),
            user=os.environ.get('DB_USER', ''),
            password=os.environ.get('DB_PASSWORD', ''),
        )
        try:
            with conn:
                rows = conn.execute_query(sql)

                if output_table and rows:
                    if mode in ('replace', 'truncate_insert'):
                        conn.execute_write(f'TRUNCATE TABLE {output_table}')
                    placeholders = ', '.join(['%s'] * len(rows[0]))
                    insert_sql = f'INSERT INTO {output_table} VALUES ({placeholders})'
                    for row in rows:
                        conn.execute_write(insert_sql, row)

            logger.info("Query returned %d rows", len(rows))
            return StepResult(success=True, rows_affected=len(rows))
        except Exception as e:
            logger.error("DB query step failed: %s", e)
            return StepResult(success=False, error=str(e))
