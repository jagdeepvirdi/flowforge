import csv
import logging
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)


def generate(
    rows: Iterable[tuple],
    columns: list[str],
    output_path: Path,
    delimiter: str = ',',
    include_header: bool = True,
    encoding: str = 'utf-8-sig',  # BOM for Excel CSV compatibility
) -> Path:
    """Write rows to a CSV file. Returns output_path.

    `rows` may be a list or any iterable (e.g. a streaming query result) — rows
    are written one at a time rather than requiring a fully materialized list,
    so a multi-million-row report doesn't need to fit in memory before the
    first row is written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    with open(output_path, 'w', newline='', encoding=encoding) as f:
        writer = csv.writer(f, delimiter=delimiter)
        if include_header:
            writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
            row_count += 1
    logger.info("CSV report written: %s (%d rows)", output_path, row_count)
    return output_path
