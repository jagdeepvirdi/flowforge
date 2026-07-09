"""Delete generated output files older than the configured TTL."""
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DIR      = 'output'
_DEFAULT_TTL_DAYS = 7


def cleanup_output_files(
    output_dir: str | None = None,
    ttl_days: int | None = None,
) -> dict:
    """
    Delete files in output_dir that are older than ttl_days.

    Returns a summary dict: {deleted, bytes_freed, errors}
    """
    directory = Path(
        output_dir
        or os.environ.get('FLOWFORGE_OUTPUT_DIR', _DEFAULT_DIR)
    )
    if ttl_days is not None:
        days = ttl_days
    else:
        from flowforge.engine.settings import get_output_ttl_days
        days = get_output_ttl_days()

    if not directory.exists():
        logger.info("Output directory does not exist, skipping cleanup: %s", directory)
        return {'deleted': 0, 'bytes_freed': 0, 'errors': 0}

    cutoff = datetime.now(UTC).timestamp() - days * 86_400
    deleted = bytes_freed = errors = 0

    for path in directory.iterdir():
        try:
            if not path.is_file():
                continue
            stat = path.stat()
            if stat.st_mtime < cutoff:
                bytes_freed += stat.st_size
                path.unlink()
                deleted += 1
                logger.debug("Deleted expired output file: %s", path)
        except Exception as e:
            logger.warning("Could not delete %s: %s", path, e)
            errors += 1

    logger.info(
        "Output cleanup: %d file(s) deleted (%.2f MB freed), %d error(s) [TTL=%dd, dir=%s]",
        deleted, bytes_freed / 1_048_576, errors, days, directory,
    )
    return {'deleted': deleted, 'bytes_freed': bytes_freed, 'errors': errors}
