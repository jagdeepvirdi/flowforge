import logging
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class OneDriveUploadStep(BaseStep):
    """Uploads a file to Microsoft OneDrive and stores the shareable URL in step context."""

    step_type = 'onedrive_upload'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render
        from flowforge.storage.onedrive import upload_file

        file_path = Path(render(self.config.get('file_path', ''), context))
        folder_id = render(self.config.get('folder_id', 'root'), context)
        rename_to = render(self.config.get('rename_to', ''), context)
        user_email = render(self.config.get('user_email', ''), context)

        if rename_to:
            renamed = file_path.parent / rename_to
            file_path.rename(renamed)
            file_path = renamed

        try:
            drive_url = upload_file(file_path, folder_id, make_shareable=True, user_email=user_email)
            logger.info("Uploaded '%s' → %s", file_path.name, drive_url)
            return StepResult(success=True, drive_url=drive_url)
        except Exception as e:
            logger.error("OneDrive upload failed: %s", e)
            return StepResult(success=False, error=str(e))
