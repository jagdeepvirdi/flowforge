import logging
import os
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class ReportStep(BaseStep):
    """Generates a report file (Excel / CSV / PDF) from a configured report_config."""

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        report_cfg = self._load_config()

        query = render(report_cfg.get('query', ''), context)
        fmt = report_cfg.get('format', 'excel').lower()
        output_filename = render(report_cfg.get('output_filename', 'report'), context)
        output_dir = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', './output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        conn = self._get_connection(report_cfg)
        try:
            with conn:
                rows = conn.execute_query(query)

            columns = report_cfg.get('columns') or (
                [f'col{i}' for i in range(len(rows[0]))] if rows else []
            )

            if fmt == 'excel':
                from flowforge.reports.excel_report import generate
                tmpl = Path(report_cfg['template_path']) if report_cfg.get('template_path') else None
                generate(rows, columns, output_path,
                         sheet_name=report_cfg.get('sheet_name', 'Sheet1'),
                         template_path=tmpl)
            elif fmt == 'csv':
                from flowforge.reports.csv_report import generate
                generate(rows, columns, output_path)
            elif fmt == 'pdf':
                from flowforge.reports.pdf_report import generate
                generate(rows, columns, output_path, title=report_cfg.get('title', ''))
            else:
                return StepResult(success=False, error=f"Unknown report format: {fmt}")

            logger.info("Report generated: %s (%d rows)", output_path, len(rows))
            return StepResult(success=True, output_path=str(output_path), rows_affected=len(rows))
        except Exception as e:
            logger.error("Report step failed: %s", e)
            return StepResult(success=False, error=str(e))

    def _load_config(self) -> dict:
        report_config_id = self.config.get('report_config_id')
        if report_config_id:
            from flowforge.db.models import ReportConfig, db
            row = db.session.get(ReportConfig, report_config_id)
            if not row:
                raise ValueError(f"ReportConfig not found: {report_config_id}")
            return {
                'connection_id': row.connection_id,
                'query': row.query,
                'format': row.format,
                'template_path': row.template_path,
                'output_filename': row.output_filename,
                'title': row.title,
                'sheet_name': row.sheet_name,
                'columns': row.columns,
            }
        return self.config.get('inline_config', {})

    def _get_connection(self, report_cfg: dict):
        connection_id = report_cfg.get('connection_id')
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
