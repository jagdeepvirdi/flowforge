import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_client():
    try:
        import boto3
    except ImportError:
        raise ImportError("AWS S3 support requires: pip install 'flowforge[s3]'")

    kwargs: dict = {}
    region = os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION')
    if region:
        kwargs['region_name'] = region
    access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    if access_key and secret_key:
        kwargs['aws_access_key_id'] = access_key
        kwargs['aws_secret_access_key'] = secret_key
    # If neither is set, boto3 falls back to its default credential chain
    # (shared config file, instance/task role, etc.)
    return boto3.client('s3', **kwargs)


def upload_file(file_path: Path, bucket: str, key: str, make_shareable: bool = False, expires_in: int = 3600) -> str:
    """Upload a file to S3. Returns an s3:// URI, or a presigned HTTPS URL if make_shareable=True."""
    client = _get_client()
    client.upload_file(str(file_path), bucket, key)
    logger.info("Uploaded '%s' to s3://%s/%s", file_path.name, bucket, key)

    if make_shareable:
        return client.generate_presigned_url(
            'get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=expires_in,
        )
    return f's3://{bucket}/{key}'
