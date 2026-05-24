import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_GRAPH_BASE = 'https://graph.microsoft.com/v1.0'
_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB — Graph API small-file threshold


def _get_token() -> str:
    try:
        import msal
    except ImportError:
        raise ImportError("OneDrive support requires: pip install 'flowforge[microsoft365]'")

    tenant_id = os.environ.get('MICROSOFT_TENANT_ID', '')
    client_id = os.environ.get('MICROSOFT_CLIENT_ID', '')
    client_secret = os.environ.get('MICROSOFT_CLIENT_SECRET', '')

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f'https://login.microsoftonline.com/{tenant_id}',
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
    if 'access_token' not in result:
        raise RuntimeError(f"MSAL token acquisition failed: {result.get('error_description')}")
    return result['access_token']


def upload_file(
    file_path: Path,
    folder_id: str,
    make_shareable: bool = False,
    user_email: str = '',
) -> str:
    """Upload a file to a user's OneDrive via Microsoft Graph API.

    folder_id: OneDrive item ID of the target folder, or 'root' for the root.
    user_email: M365 user whose OneDrive to use; defaults to MICROSOFT_SENDER_EMAIL.
    Returns: item ID, or anonymous view URL when make_shareable=True.
    """
    try:
        import requests
    except ImportError:
        raise ImportError("OneDrive support requires: pip install requests")

    user = user_email or os.environ.get('MICROSOFT_SENDER_EMAIL', '')
    if not user:
        raise ValueError(
            "OneDrive upload requires MICROSOFT_SENDER_EMAIL or explicit user_email"
        )

    token = _get_token()
    headers = {'Authorization': f'Bearer {token}'}
    filename = file_path.name
    file_size = file_path.stat().st_size

    # Build the upload-path prefix relative to the target folder
    if folder_id and folder_id.lower() != 'root':
        path_prefix = f'{_GRAPH_BASE}/users/{user}/drive/items/{folder_id}:/{filename}:'
    else:
        path_prefix = f'{_GRAPH_BASE}/users/{user}/drive/root:/{filename}:'

    if file_size <= _CHUNK_SIZE:
        item_id = _upload_direct(path_prefix, file_path, headers, requests)
    else:
        item_id = _upload_session(path_prefix, file_path, file_size, headers, requests)

    logger.info("Uploaded '%s' to OneDrive (id=%s)", filename, item_id)

    if make_shareable:
        resp = requests.post(
            f'{_GRAPH_BASE}/users/{user}/drive/items/{item_id}/createLink',
            json={'type': 'view', 'scope': 'anonymous'},
            headers={**headers, 'Content-Type': 'application/json'},
        )
        resp.raise_for_status()
        url = resp.json()['link']['webUrl']
        logger.info("Created shareable link for '%s': %s", filename, url)
        return url

    return item_id


def _upload_direct(path_prefix: str, file_path: Path, headers: dict, requests) -> str:
    with open(file_path, 'rb') as f:
        data = f.read()
    resp = requests.put(
        f'{path_prefix}/content',
        data=data,
        headers={**headers, 'Content-Type': 'application/octet-stream'},
    )
    resp.raise_for_status()
    return resp.json()['id']


def _upload_session(
    path_prefix: str, file_path: Path, file_size: int, headers: dict, requests
) -> str:
    session_resp = requests.post(
        f'{path_prefix}/createUploadSession',
        json={'item': {'@microsoft.graph.conflictBehavior': 'rename'}},
        headers={**headers, 'Content-Type': 'application/json'},
    )
    session_resp.raise_for_status()
    upload_url = session_resp.json()['uploadUrl']

    item_id = None
    with open(file_path, 'rb') as f:
        offset = 0
        while True:
            chunk = f.read(_CHUNK_SIZE)
            if not chunk:
                break
            end = offset + len(chunk) - 1
            resp = requests.put(
                upload_url,
                data=chunk,
                headers={
                    'Content-Length': str(len(chunk)),
                    'Content-Range': f'bytes {offset}-{end}/{file_size}',
                },
            )
            resp.raise_for_status()
            offset += len(chunk)
            if resp.status_code in (200, 201):
                item_id = resp.json()['id']

    if not item_id:
        raise RuntimeError("Upload session completed without returning an item ID")
    return item_id
