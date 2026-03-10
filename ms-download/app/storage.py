import logging
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from app.config import settings

logger = logging.getLogger(__name__)

def get_presigned_download_url(minio_key: str, expires_hours: int = 1) -> str:
    """
    Génère une URL présignée via ent_minio:9000 (interne),
    puis remplace l'host par localhost:9000 pour que le navigateur puisse y accéder.
    """
    client = Minio(
        endpoint=settings.MINIO_ENDPOINT,   # ent_minio:9000
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    try:
        url = client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=minio_key,
            expires=timedelta(hours=expires_hours),
        )
        # Remplacer l'adresse interne par l'adresse publique
        url = url.replace(settings.MINIO_ENDPOINT, settings.MINIO_ENDPOINT_PUBLIC)
        return url
    except S3Error as e:
        logger.error(f"Erreur MinIO presigned URL : {e}")
        raise
