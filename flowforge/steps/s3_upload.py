"""S3 upload step — upload a file to AWS S3.

Config:
    file_path       Path to the file to upload (supports Jinja2, e.g. {{ steps.report.output_path }})
    bucket          Target S3 bucket
    key             Object key (default: file's own name, or rename_to if set)
    rename_to       Optional — rename the local file before upload
    presigned_url   bool (default true) — return a time-limited HTTPS URL instead of an s3:// URI

Credentials: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION env vars,
or boto3's default credential chain (instance role, shared config, etc.) if unset.
"""
import logging
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class S3UploadStep(BaseStep):
    """Uploads a file to AWS S3 and stores the resulting URL in step context."""

    step_type = 's3_upload'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render
        from flowforge.storage.s3 import upload_file

        file_path = Path(render(self.config.get('file_path', ''), context))
        bucket    = render(self.config.get('bucket', ''), context)
        rename_to = render(self.config.get('rename_to', ''), context)
        key       = render(self.config.get('key', ''), context) or rename_to or file_path.name
        presigned = bool(self.config.get('presigned_url', True))

        if rename_to:
            renamed = file_path.parent / rename_to
            file_path.rename(renamed)
            file_path = renamed

        try:
            url = upload_file(file_path, bucket, key, make_shareable=presigned)
            logger.info("Uploaded '%s' → %s", file_path.name, url)
            return StepResult(success=True, drive_url=url)
        except Exception as e:
            logger.exception("S3 upload failed")
            return StepResult(success=False, error=str(e))
