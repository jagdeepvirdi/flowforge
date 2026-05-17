import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate(
    rows: list[tuple],
    columns: list[str],
    output_path: Path,
    delimiter: str = ',',
    include_header: bool = True,
    encoding: str = 'utf-8-sig',  # BOM for Excel CSV compatibility
) -> Path:
    """Write rows to a CSV file. Returns output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding=encoding) as f:
        writer = csv.writer(f, delimiter=delimiter)
        if include_header:
            writer.writerow(columns)
        writer.writerows(rows)
    logger.info("CSV report written: %s (%d rows)", output_path, len(rows))
    return output_path
