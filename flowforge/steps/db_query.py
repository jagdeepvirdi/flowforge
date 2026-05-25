import html as _html
import logging
from typing import Any

from flowforge.steps.base import BaseStep, StepResult, validate_identifier

logger = logging.getLogger(__name__)

_VALID_MODES = {'replace', 'append', 'truncate_insert'}


def _render_table_html(rows: list[dict]) -> str:
    if not rows:
        return ''
    cols = list(rows[0].keys())
    th_s = 'padding:6px 12px;text-align:left;background:#f1f5f9;color:#475569;font-size:12px;font-weight:600;border-bottom:2px solid #e2e8f0'
    td_s = 'padding:6px 12px;font-size:13px;color:#1e293b;border-bottom:1px solid #e2e8f0'
    tbl_s = 'border-collapse:collapse;width:100%;font-family:Arial,Helvetica,sans-serif'
    ths = ''.join(f'<th style="{th_s}">{_html.escape(str(c))}</th>' for c in cols)
    trs = ''.join(
        '<tr>' + ''.join(
            f'<td style="{td_s}">{_html.escape(str(row.get(c, "")))}</td>' for c in cols
        ) + '</tr>'
        for row in rows
    )
    return f'<table style="{tbl_s}"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'


def _render_kv_html(rows: list[dict]) -> str:
    if not rows:
        return ''
    dt_s = 'font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 2px 0'
    dd_s = 'font-size:14px;color:#1e293b;margin:0 0 10px 0'
    items = ''.join(
        f'<dt style="{dt_s}">{_html.escape(str(k))}</dt>'
        f'<dd style="{dd_s}">{_html.escape(str(v))}</dd>'
        for k, v in rows[0].items()
    )
    return f'<dl style="margin:0;padding:0">{items}</dl>'


class DbQueryStep(BaseStep):
    """Executes a SQL query and optionally writes results to an output table."""

    step_type = 'db_query'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        sql = render(self.config['query'], context)
        output_table = self.config.get('output_table', '')
        mode = self.config.get('mode', 'replace')
        capture_rows = bool(self.config.get('capture_rows', False))
        row_limit = int(self.config.get('row_limit', 100))

        if output_table and mode not in _VALID_MODES:
            return StepResult(success=False, error=f"Invalid mode '{mode}'. Must be one of: {', '.join(_VALID_MODES)}")

        if output_table:
            try:
                validate_identifier(output_table, 'output_table')
            except ValueError as e:
                return StepResult(success=False, error=str(e))

        output_variable = self.config.get('output_variable', '').strip()

        conn = self._get_connection()
        try:
            with conn:
                if capture_rows:
                    raw_rows, columns = conn.execute_query_with_columns(sql)
                else:
                    raw_rows = conn.execute_query(sql)
                    columns = []

                if output_table and raw_rows:
                    if mode in ('replace', 'truncate_insert'):
                        # Table name is from trusted config (not user input), so
                        # direct interpolation here is acceptable.
                        conn.execute_write(f'TRUNCATE TABLE {output_table}')  # nosec B608
                    placeholders = ', '.join(['%s'] * len(raw_rows[0]))
                    insert_sql = f'INSERT INTO {output_table} VALUES ({placeholders})'  # nosec B608
                    for row in raw_rows:
                        conn.execute_write(insert_sql, tuple(row))

            output_vars: dict = {}
            result_rows: list[dict] = []
            table_html = ''
            kv_html = ''

            if output_variable and raw_rows:
                output_vars[output_variable] = raw_rows[0][0]

            if capture_rows and columns and raw_rows:
                result_rows = [dict(zip(columns, row)) for row in raw_rows[:row_limit]]
                table_html = _render_table_html(result_rows)
                kv_html = _render_kv_html(result_rows)

            logger.info("Query returned %d rows", len(raw_rows))
            return StepResult(
                success=True,
                rows_affected=len(raw_rows),
                output_variables=output_vars,
                rows=result_rows,
                table_html=table_html,
                kv_html=kv_html,
            )
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
