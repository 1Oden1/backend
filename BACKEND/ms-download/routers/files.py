from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import DownloadUrlResponse, FileMetadataResponse
from typing import List
from services.auth_client import require_authenticated
from services.cassandra import get_file_by_id, get_files_by_cours
from services.minio import get_presigned_url, get_client
from config import settings

router = APIRouter(prefix="/files", tags=["Fichiers"])


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.get("/{file_id}/url", response_model=DownloadUrlResponse)
def get_download_url(file_id: str, authorization: str = Header(None)):
    require_authenticated(get_token(authorization))
    file_meta = get_file_by_id(file_id)
    download_url = get_presigned_url(file_meta["minio_path"], expires_minutes=60)
    return DownloadUrlResponse(
        file_id=file_id,
        original_name=file_meta["original_name"],
        download_url=download_url,
        expires_in="60 minutes"
    )


@router.get("/{file_id}/stream")
def stream_file(file_id: str, authorization: str = Header(None)):
    require_authenticated(get_token(authorization))
    file_meta = get_file_by_id(file_id)
    client = get_client()
    try:
        original_name = file_meta["original_name"]
        response = client.get_object(settings.MINIO_BUCKET, file_meta["minio_path"])
        return StreamingResponse(
            response,
            media_type=file_meta.get("content_type", "application/octet-stream"),
            headers={"Content-Disposition": "attachment; filename=" + original_name}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Fichier non trouve: " + str(e))


@router.get("/cours/{cours_id}", response_model=List[FileMetadataResponse])
def list_files_by_cours(cours_id: int, authorization: str = Header(None)):
    require_authenticated(get_token(authorization))
    return get_files_by_cours(cours_id)