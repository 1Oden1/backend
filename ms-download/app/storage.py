import logging
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from app.config import settings

logger = logging.getLogger(__name__)

def get_presigned_download_url(minio_key: str, expires_hours: int = 1) -> str:
    # Client interne pour les opérations normales
    client_internal = Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    # Client public pour générer les URLs présignées avec le bon hostname
    client_public = Minio(
        endpoint=settings.MINIO_ENDPOINT_PUBLIC,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    try:
        url = client_public.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=minio_key,
            expires=timedelta(hours=expires_hours),
        )
        return url
    except S3Error as e:
        logger.error(f"Erreur MinIO presigned URL : {e}")
        raise