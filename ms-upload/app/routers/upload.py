import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth import get_current_user, require_role
from app.config import settings
from app.database import get_session
from app.schemas import DeleteResponse, FileUploadResponse
from app.storage import delete_file_from_minio, upload_file_to_minio

router = APIRouter()


def _validate_file(filename: str, size: int):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extension '.{ext}' non autorisée. Acceptées : {settings.ALLOWED_EXTENSIONS}",
        )
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux. Maximum : {settings.MAX_FILE_SIZE_MB} Mo.",
        )


@router.post("/", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(..., description="Fichier à uploader"),
    title: str = Form(..., description="Titre du document"),
    description: Optional[str] = Form(None, description="Description du contenu"),
    category: str = Form(..., description="cours | td | tp | examen | autre"),
    module: str = Form(..., description="Module concerné (ex: Réseaux, BDD)"),
    is_public: bool = Form(True, description="Visible par tous les étudiants"),
    user: dict = Depends(require_role("enseignant", "admin")),
):
    """
    **Upload d'un fichier pédagogique** *(enseignants et admins uniquement)*.
    """
    file_data = await file.read()
    safe_name = os.path.basename(file.filename)

    _validate_file(safe_name, len(file_data))

    file_id = uuid.uuid4()
    minio_key = f"{category}/{module}/{file_id}/{safe_name}"
    content_type = file.content_type or "application/octet-stream"
    upload_date = datetime.utcnow()

    if not upload_file_to_minio(file_data, minio_key, content_type):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec du stockage dans MinIO.",
        )

    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    session.execute(
        """
        INSERT INTO files (
            file_id, owner_id, owner_name, title, description,
            category, module, filename, content_type, size_bytes,
            minio_key, upload_date, is_public
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            file_id,
            user.get("sub"),
            user.get("name", user.get("preferred_username", "Inconnu")),
            title,
            description,
            category,
            module,
            safe_name,
            content_type,
            len(file_data),
            minio_key,
            upload_date,
            is_public,
        ),
    )

    return FileUploadResponse(
        file_id=str(file_id),
        title=title,
        filename=safe_name,
        size_bytes=len(file_data),
        category=category,
        module=module,
        minio_key=minio_key,
        upload_date=upload_date,
    )


@router.delete("/{file_id}", response_model=DeleteResponse)
def delete_file(
    file_id: str,
    user: dict = Depends(require_role("enseignant", "admin")),
):
    """
    **Suppression d'un fichier** *(propriétaire ou admin uniquement)*.
    """
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    row = session.execute(
        "SELECT file_id, owner_id, minio_key FROM files WHERE file_id = %s",
        (uuid.UUID(file_id),),
    ).one()

    if not row:
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    user_roles = user.get("realm_access", {}).get("roles", [])
    if row.owner_id != user.get("sub") and "admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres fichiers.")

    delete_file_from_minio(row.minio_key)
    session.execute("DELETE FROM files WHERE file_id = %s", (uuid.UUID(file_id),))

    return DeleteResponse(file_id=file_id, message="Fichier supprimé avec succès.")
