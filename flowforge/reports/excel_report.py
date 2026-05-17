import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate(
    rows: list[tuple],
    columns: list[str],
    output_path: Path,
    sheet_name: str = 'Sheet1',
    template_path: Path | None = None,
) -> Path:
    """Write rows to an Excel file. Returns output_path."""
    try:
        from openpyxl import Workbook, load_workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        raise ImportError("openpyxl is required: pip install openpyxl")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if template_path and template_path.exists():
        book = load_workbook(template_path)
        ws = book.active
        start_row = ws.max_row + 1
    else:
        book = Workbook()
        ws = book.active
        ws.title = sheet_name
        # Header row: bold + light grey fill
        header_fill = PatternFill(fill_type='solid', fgColor='D9D9D9')
        for col_idx, col_name in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = Font(bold=True)
            cell.fill = header_fill
        start_row = 2

    for row_idx, row in enumerate(rows, start_row):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-width columns (capped at 60 chars)
    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

    book.save(output_path)
    book.close()
    logger.info("Excel report written: %s (%d rows)", output_path, len(rows))
    return output_path
