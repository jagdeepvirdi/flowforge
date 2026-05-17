import io
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']


def _get_service():
    """Build a Drive API service using a service account file or OAuth2 credentials."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "google-api-python-client is required: pip install google-api-python-client"
        )

    sa_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if sa_file:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(sa_file, scopes=_DRIVE_SCOPES)
    else:
        # OAuth2 — shares credentials with Gmail when same Google account
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=None,
            refresh_token=os.environ.get('GMAIL_REFRESH_TOKEN', ''),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get('GMAIL_CLIENT_ID', ''),
            client_secret=os.environ.get('GMAIL_CLIENT_SECRET', ''),
            scopes=_DRIVE_SCOPES,
        )
        creds.refresh(Request())

    return build('drive', 'v3', credentials=creds)


def upload_file(file_path: Path, folder_id: str, make_shareable: bool = False) -> str:
    """Upload a file to Google Drive. Returns file ID, or shareable URL if make_shareable=True."""
    from googleapiclient.http import MediaFileUpload

    service = _get_service()
    metadata = {
        'name': file_path.name,
        'parents': [folder_id] if folder_id else [],
    }
    media = MediaFileUpload(str(file_path))
    result = service.files().create(body=metadata, media_body=media, fields='id').execute()
    file_id = result['id']
    logger.info("Uploaded '%s' to Drive (id=%s)", file_path.name, file_id)

    if make_shareable:
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()
        return f"https://drive.google.com/file/d/{file_id}/view?usp=drive_link"

    return file_id


def download_file(file_id: str, destination: Path) -> None:
    """Download a file from Google Drive by its ID."""
    from googleapiclient.http import MediaIoBaseDownload

    service = _get_service()
    request = service.files().get_media(fileId=file_id)
    with io.FileIO(str(destination), mode='wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    logger.info("Downloaded Drive file %s → %s", file_id, destination)


def create_folder(name: str, parent_id: str | None = None) -> str:
    """Create a folder in Google Drive. Returns the folder ID."""
    service = _get_service()
    metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id] if parent_id else [],
    }
    result = service.files().create(body=metadata, fields='id').execute()
    folder_id = result['id']
    logger.info("Created Drive folder '%s' (id=%s)", name, folder_id)
    return folder_id
