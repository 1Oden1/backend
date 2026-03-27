from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException
from config import settings
from datetime import timedelta


def get_client() -> Minio:
    return Minio(
        f"{settings.MINIO_URL}:{settings.MINIO_PORT}",
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False
    )


def get_presigned_url(object_name: str, expires_minutes: int = 60) -> str:
    """Génère une URL signée pour télécharger un fichier depuis MinIO"""
    client = get_client()
    try:
        url = client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_name,
            expires=timedelta(minutes=expires_minutes)
        )
        # Remplace host Docker par localhost pour le navigateur
        url = url.replace("minio:9000", "localhost:9000")
        return url
    except S3Error as e:
        raise HTTPException(status_code=404, detail=f"Fichier non trouvé dans MinIO: {e}")


def file_exists(object_name: str) -> bool:
    """Vérifie si un fichier existe dans MinIO"""
    client = get_client()
    try:
        client.stat_object(settings.MINIO_BUCKET, object_name)
        return True
    except S3Error:
        return False