import logging
import os
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class ReportStep(BaseStep):
    """Generates a report file (Excel / CSV / PDF) from a configured report_config."""

    step_type = 'report'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render, render_sql

        report_cfg = self._load_config()

        query = render_sql(report_cfg.get('query', ''), context)
        fmt = report_cfg.get('format', 'excel').lower()
        output_filename = render(report_cfg.get('output_filename', 'report'), context)
        output_dir = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', './output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        conn = self._get_connection(report_cfg)
        try:
            with conn:
                rows, columns = conn.execute_query_with_columns(query)

            if report_cfg.get('columns'):
                columns = report_cfg['columns']

            if fmt == 'excel':
                from flowforge.reports.excel_report import generate
                tmpl = _resolve_template_path(report_cfg.get('template_path'))
                generate(rows, columns, output_path,
                         sheet_name=report_cfg.get('sheet_name', 'Sheet1'),
                         template_path=tmpl)
            elif fmt == 'csv':
                from flowforge.reports.csv_report import generate
                generate(rows, columns, output_path)
            elif fmt == 'pdf':
                from flowforge.reports.pdf_report import generate
                generate(rows, columns, output_path, title=report_cfg.get('title', ''))
            elif fmt == 'json':
                from flowforge.reports.json_report import generate
                generate(rows, columns, output_path)
            else:
                return StepResult(success=False, error=f"Unknown report format: {fmt}")

            from flowforge.crypto import output_encryption_enabled, encrypt_file
            if output_encryption_enabled():
                output_path = encrypt_file(output_path)

            logger.info("Report generated: %s (%d rows)", output_path, len(rows))
            import flowforge.audit as audit
            audit.log_report_exported(
                pipeline_name=context.get('pipeline_name', ''),
                step_name=self.name,
                output_filename=output_filename,
                row_count=len(rows),
                fmt=fmt,
            )
            return StepResult(success=True, output_path=str(output_path), rows_affected=len(rows))
        except Exception as e:
            logger.exception("Report step failed")
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


def _resolve_template_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    template_root = Path(os.environ.get('FLOWFORGE_TEMPLATE_DIR', './templates')).resolve()
    resolved = (template_root / raw).resolve()
    if not str(resolved).startswith(str(template_root) + os.sep):
        raise ValueError(
            f"Template path {raw!r} is outside FLOWFORGE_TEMPLATE_DIR ({template_root})"
        )
    return resolved
