import io
import logging
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from app.config import settings

logger = logging.getLogger(__name__)


def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket_exists(client: Minio):
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
        logger.info(f"Bucket '{settings.MINIO_BUCKET}' créé.")


def upload_file_to_minio(file_data: bytes, minio_key: str, content_type: str) -> bool:
    client = get_minio_client()
    ensure_bucket_exists(client)
    try:
        client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=minio_key,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )
        return True
    except S3Error as e:
        logger.error(f"Erreur MinIO upload : {e}")
        return False


def delete_file_from_minio(minio_key: str) -> bool:
    client = get_minio_client()
    try:
        client.remove_object(settings.MINIO_BUCKET, minio_key)
        return True
    except S3Error as e:
        logger.error(f"Erreur MinIO delete : {e}")
        return False


def get_presigned_url(minio_key: str, expires_hours: int = 1) -> str:
    client = get_minio_client()
    return client.presigned_get_object(
        settings.MINIO_BUCKET,
        minio_key,
        expires=timedelta(hours=expires_hours),
    )
