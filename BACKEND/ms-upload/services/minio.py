from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException
from config import settings
import io


def get_client() -> Minio:
    return Minio(
        f"{settings.MINIO_URL}:{settings.MINIO_PORT}",
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False
    )


def ensure_bucket():
    """Crée le bucket s'il n'existe pas"""
    client = get_client()
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur MinIO bucket: {e}")


def upload_file(file_data: bytes, filename: str, content_type: str) -> str:
    """Upload un fichier dans MinIO et retourne le nom de l'objet"""
    ensure_bucket()
    client = get_client()

    object_name = f"cours/{filename}"
    try:
        client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur upload MinIO: {e}")

    return object_name