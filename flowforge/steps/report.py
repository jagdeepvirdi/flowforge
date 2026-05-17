import logging
import os
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class ReportStep(BaseStep):
    """Generates a report file (Excel / CSV / PDF) from a configured report_config."""

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.connections.postgres import PostgreSQLConnection
        from flowforge.engine.context import render

        # Phase 1: load report_config from DB via report_config_id.
        # Until then, inline_config is used for testing.
        report_cfg = self.config.get('inline_config', {})

        query = render(report_cfg.get('query', ''), context)
        fmt = report_cfg.get('format', 'excel').lower()
        output_filename = render(report_cfg.get('output_filename', 'report'), context)
        output_dir = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', './output'))
        output_path = output_dir / output_filename

        conn = PostgreSQLConnection(
            host=os.environ.get('DB_HOST', ''),
            database=os.environ.get('DB_NAME', ''),
            user=os.environ.get('DB_USER', ''),
            password=os.environ.get('DB_PASSWORD', ''),
        )
        try:
            with conn:
                rows = conn.execute_query(query)

            columns = report_cfg.get('columns', [])
            if not columns and rows:
                columns = [f'col{i}' for i in range(len(rows[0]))]

            if fmt == 'excel':
                from flowforge.reports.excel_report import generate
                sheet = report_cfg.get('sheet_name', 'Sheet1')
                tmpl = Path(report_cfg['template_path']) if report_cfg.get('template_path') else None
                generate(rows, columns, output_path, sheet_name=sheet, template_path=tmpl)
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
