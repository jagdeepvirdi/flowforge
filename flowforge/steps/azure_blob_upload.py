"""Azure Blob upload step — upload a file to Azure Blob Storage.

Config:
    file_path       Path to the file to upload (supports Jinja2, e.g. {{ steps.report.output_path }})
    container       Target Blob Storage container
    blob_name       Blob name (default: file's own name, or rename_to if set)
    rename_to       Optional — rename the local file before upload
    shareable_url   bool (default true) — append a read-only SAS token to the URL
                    (requires AZURE_STORAGE_ACCOUNT_KEY; otherwise the plain blob URL is returned)

Credentials: AZURE_STORAGE_CONNECTION_STRING env var, or
AZURE_STORAGE_ACCOUNT_URL (+ optionally AZURE_STORAGE_ACCOUNT_KEY) as a fallback.
"""
import logging
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class AzureBlobUploadStep(BaseStep):
    """Uploads a file to Azure Blob Storage and stores the resulting URL in step context."""

    step_type = 'azure_blob_upload'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render
        from flowforge.storage.azure_blob import upload_file

        file_path = Path(render(self.config.get('file_path', ''), context))
        container = render(self.config.get('container', ''), context)
        rename_to = render(self.config.get('rename_to', ''), context)
        blob_name = render(self.config.get('blob_name', ''), context) or rename_to or file_path.name
        shareable = bool(self.config.get('shareable_url', True))

        if rename_to:
            renamed = file_path.parent / rename_to
            file_path.rename(renamed)
            file_path = renamed

        try:
            url = upload_file(file_path, container, blob_name, make_shareable=shareable)
            logger.info("Uploaded '%s' → %s", file_path.name, url)
            return StepResult(success=True, drive_url=url)
        except Exception as e:
            logger.exception("Azure Blob upload failed")
            return StepResult(success=False, error=str(e))
