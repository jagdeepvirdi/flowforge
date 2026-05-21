import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate(
    rows: list[tuple],
    columns: list[str],
    output_path: Path,
    indent: int = 2,
) -> Path:
    """Write rows to a JSON file as an array of objects. Returns output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [dict(zip(columns, row)) for row in rows]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, default=str)
    logger.info("JSON report written: %s (%d rows)", output_path, len(rows))
    return output_path
