import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.auth import require_admin
from app.config import settings
from app.database_cassandra import get_session
from app.schemas import FileListResponse, FileRead, FileVisibilityUpdate
from app.storage import delete_file_from_minio, get_presigned_url, upload_file_to_minio
from app.routers.audit import log_action

router = APIRouter(prefix="/fichiers", tags=["Fichiers"])

MAX_FILE_SIZE_MB   = 50
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "xlsx", "jpg", "jpeg", "png", "mp4", "zip", "txt", "md"}


def _validate_file(filename: str, size: int):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Extension '.{ext}' non autorisée.")
    if size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Fichier trop volumineux. Maximum : {MAX_FILE_SIZE_MB} Mo.")


def _row_to_schema(r) -> FileRead:
    return FileRead(
        file_id=str(r.file_id),
        owner_id=r.owner_id,
        owner_name=r.owner_name,
        title=r.title,
        description=r.description,
        category=r.category,
        module=r.module,
        filename=r.filename,
        content_type=r.content_type,
        size_bytes=r.size_bytes,
        upload_date=r.upload_date,
        is_public=r.is_public,
        minio_key=r.minio_key,
    )


@router.get(
    "/",
    response_model=FileListResponse,
    summary="Lister tous les fichiers (publics et privés)",
)
def list_all_files(
    category: Optional[str] = Query(None),
    module:   Optional[str] = Query(None),
    _: dict = Depends(require_admin),
):
    """L'admin voit tous les fichiers, y compris les non-publics."""
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    if category:
        rows = session.execute(
            "SELECT * FROM files WHERE category = %s ALLOW FILTERING", (category,)
        )
    elif module:
        rows = session.execute(
            "SELECT * FROM files WHERE module = %s ALLOW FILTERING", (module,)
        )
    else:
        rows = session.execute("SELECT * FROM files")

    files = [_row_to_schema(r) for r in rows]
    return FileListResponse(total=len(files), files=files)


@router.get(
    "/{file_id}/download",
    summary="Obtenir un lien de téléchargement (toujours accessible pour l'admin)",
)
def get_download_link(
    file_id: str,
    expires_hours: int = Query(1, ge=1, le=24),
    _: dict = Depends(require_admin),
):
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    row = session.execute(
        "SELECT file_id, filename, minio_key FROM files WHERE file_id = %s",
        (uuid.UUID(file_id),),
    ).one()
    if not row:
        raise HTTPException(404, "Fichier introuvable.")

    url = get_presigned_url(row.minio_key, expires_hours)
    return {"file_id": file_id, "filename": row.filename, "download_url": url, "expires_in": f"{expires_hours}h"}


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Uploader un fichier pédagogique",
)
async def upload_file(
    file:        UploadFile        = File(...),
    title:       str               = Form(...),
    description: Optional[str]     = Form(None),
    category:    str               = Form(...),
    module:      str               = Form(...),
    is_public:   bool              = Form(True),
    admin: dict  = Depends(require_admin),
):
    file_data = await file.read()
    safe_name = os.path.basename(file.filename)
    _validate_file(safe_name, len(file_data))

    file_id     = uuid.uuid4()
    minio_key   = f"{category}/{module}/{file_id}/{safe_name}"
    content_type = file.content_type or "application/octet-stream"
    upload_date  = datetime.utcnow()

    if not upload_file_to_minio(file_data, minio_key, content_type):
        raise HTTPException(500, "Échec du stockage dans MinIO.")

    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    session.execute(
        """
        INSERT INTO files
            (file_id, owner_id, owner_name, title, description,
             category, module, filename, content_type, size_bytes,
             minio_key, upload_date, is_public)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            file_id,
            admin.get("sub"),
            admin.get("name", admin.get("preferred_username", "admin")),
            title, description, category, module, safe_name,
            content_type, len(file_data), minio_key, upload_date, is_public,
        ),
    )

    log_action(admin["sub"], "UPLOAD_FILE", "file", str(file_id), f"{title} | {safe_name}")
    return {"file_id": str(file_id), "title": title, "filename": safe_name,
            "size_bytes": len(file_data), "minio_key": minio_key, "message": "Fichier uploadé avec succès."}


@router.patch(
    "/{file_id}/visibility",
    summary="Modifier la visibilité d'un fichier (public / privé)",
)
def update_visibility(
    file_id: str,
    body: FileVisibilityUpdate,
    admin: dict = Depends(require_admin),
):
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    row = session.execute(
        "SELECT file_id FROM files WHERE file_id = %s", (uuid.UUID(file_id),)
    ).one()
    if not row:
        raise HTTPException(404, "Fichier introuvable.")

    session.execute(
        "UPDATE files SET is_public = %s WHERE file_id = %s",
        (body.is_public, uuid.UUID(file_id)),
    )
    log_action(admin["sub"], "UPDATE_FILE_VISIBILITY", "file", file_id, f"is_public={body.is_public}")
    return {"file_id": file_id, "is_public": body.is_public}


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un fichier (Cassandra + MinIO)",
)
def delete_file(file_id: str, admin: dict = Depends(require_admin)):
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    row = session.execute(
        "SELECT file_id, minio_key FROM files WHERE file_id = %s", (uuid.UUID(file_id),)
    ).one()
    if not row:
        raise HTTPException(404, "Fichier introuvable.")

    delete_file_from_minio(row.minio_key)
    session.execute("DELETE FROM files WHERE file_id = %s", (uuid.UUID(file_id),))
    log_action(admin["sub"], "DELETE_FILE", "file", file_id, row.minio_key)
