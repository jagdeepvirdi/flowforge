import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_container_client(container: str):
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        raise ImportError("Azure Blob support requires: pip install 'flowforge[azure_blob]'")

    conn_str = os.environ.get('AZURE_STORAGE_CONNECTION_STRING', '')
    if conn_str:
        service = BlobServiceClient.from_connection_string(conn_str)
    else:
        account_url = os.environ.get('AZURE_STORAGE_ACCOUNT_URL', '')
        account_key = os.environ.get('AZURE_STORAGE_ACCOUNT_KEY', '')
        if not account_url:
            raise ValueError(
                "Azure Blob upload requires AZURE_STORAGE_CONNECTION_STRING, "
                "or AZURE_STORAGE_ACCOUNT_URL (+ optionally AZURE_STORAGE_ACCOUNT_KEY)"
            )
        service = BlobServiceClient(account_url=account_url, credential=account_key or None)
    return service.get_container_client(container)


def upload_file(file_path: Path, container: str, blob_name: str, make_shareable: bool = False,
                 expires_hours: int = 24) -> str:
    """Upload a file to Azure Blob Storage. Returns the blob URL, with a SAS token
    appended if make_shareable=True and AZURE_STORAGE_ACCOUNT_KEY is set.
    """
    container_client = _get_container_client(container)
    with open(file_path, 'rb') as f:
        blob_client = container_client.upload_blob(name=blob_name, data=f, overwrite=True)
    logger.info("Uploaded '%s' to container '%s' as '%s'", file_path.name, container, blob_name)

    url = blob_client.url
    account_key = os.environ.get('AZURE_STORAGE_ACCOUNT_KEY', '')
    if make_shareable and account_key:
        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        sas = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=container,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(hours=expires_hours),
        )
        url = f'{url}?{sas}'
    return url
