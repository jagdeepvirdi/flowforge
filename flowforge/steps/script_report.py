"""Script report step — generate reports from pipeline context variables."""
import csv
import json
import logging
import os
from io import StringIO
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class ScriptReportStep(BaseStep):
    """Generate a report file from a context variable.

    Config fields:
        data_var        Name of the context variable containing the data (required)
        data_format     Format of the data in the variable: 'csv', 'json' (default: 'csv')
        format          Output report format: 'excel', 'csv', 'pdf', 'json' (default: 'excel')
        output_filename Output filename — supports {{ variables }} (required)
        columns         Optional list of column names (if not in data)
        title           Report title (for PDF)
        sheet_name      Sheet name (for Excel)
    """

    step_type = 'data_report'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        data_var = self.config.get('data_var')
        if not data_var:
            return StepResult(success=False, error='data_report: data_var is required')

        raw_data = context.get(data_var)
        if not raw_data:
            return StepResult(success=False, error=f"data_report: variable '{data_var}' is empty or not found")

        data_format = self.config.get('data_format', 'csv').lower()
        
        try:
            rows, columns = self._parse_data(raw_data, data_format)
        except Exception as e:
            return StepResult(success=False, error=f"Failed to parse data as {data_format}: {e}")

        if not rows:
            return StepResult(success=True, logs="No data found in variable; skipping report generation")

        if self.config.get('columns'):
            columns = self.config['columns']

        fmt = self.config.get('format', 'excel').lower()
        output_filename = render(self.config.get('output_filename', 'report'), context)
        output_dir = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', './output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        try:
            if fmt == 'excel':
                from flowforge.reports.excel_report import generate
                generate(rows, columns, output_path,
                         sheet_name=self.config.get('sheet_name', 'Sheet1'))
            elif fmt == 'csv':
                from flowforge.reports.csv_report import generate
                generate(rows, columns, output_path)
            elif fmt == 'pdf':
                from flowforge.reports.pdf_report import generate
                generate(rows, columns, output_path, title=self.config.get('title', ''))
            elif fmt == 'json':
                from flowforge.reports.json_report import generate
                generate(rows, columns, output_path)
            else:
                return StepResult(success=False, error=f"Unknown report format: {fmt}")

            from flowforge.crypto import output_encryption_enabled, encrypt_file
            if output_encryption_enabled():
                output_path = encrypt_file(output_path)

            logger.info("Script report generated: %s (%d rows)", output_path, len(rows))
            return StepResult(success=True, output_path=str(output_path), rows_affected=len(rows))

        except Exception as e:
            logger.exception("Script report generation failed")
            return StepResult(success=False, error=str(e))

    def _parse_data(self, raw_data: Any, fmt: str) -> tuple[list[tuple], list[str]]:
        if fmt == 'json':
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            else:
                data = raw_data
            
            if not isinstance(data, list):
                raise ValueError("JSON data must be a list of objects")
            
            if not data:
                return [], []
            
            columns = list(data[0].keys())
            rows = [tuple(obj.get(col) for col in columns) for obj in data]
            return rows, columns

        if fmt == 'csv':
            if not isinstance(raw_data, str):
                raise ValueError("CSV data must be a string")
            
            f = StringIO(raw_data.strip())
            # Try to detect delimiter
            try:
                dialect = csv.Sniffer().sniff(raw_data[:1024])
                reader = csv.reader(f, dialect)
            except:
                reader = csv.reader(f) # Fallback to default
            
            all_rows = list(reader)
            if not all_rows:
                return [], []
            
            columns = all_rows[0]
            rows = [tuple(r) for r in all_rows[1:]]
            return rows, columns

        raise ValueError(f"Unsupported data_format: {fmt}")
