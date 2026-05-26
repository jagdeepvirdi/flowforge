import logging
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class DriveUploadStep(BaseStep):
    """Uploads a file to Google Drive and stores the shareable URL in step context."""

    step_type = 'drive_upload'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render
        from flowforge.storage.google_drive import upload_file

        file_path = Path(render(self.config.get('file_path', ''), context))
        folder_id = render(self.config.get('folder_id', ''), context)
        rename_to = render(self.config.get('rename_to', ''), context)

        if rename_to:
            renamed = file_path.parent / rename_to
            file_path.rename(renamed)
            file_path = renamed

        try:
            drive_url = upload_file(file_path, folder_id, make_shareable=True)
            logger.info("Uploaded '%s' → %s", file_path.name, drive_url)
            return StepResult(success=True, drive_url=drive_url)
        except Exception as e:
            logger.exception("Drive upload failed")
            return StepResult(success=False, error=str(e))
