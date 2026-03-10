import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.config import settings
from app.database import get_session
from app.schemas import DownloadLinkResponse, FileListResponse, FileMetadata
from app.storage import get_presigned_download_url

router = APIRouter()


@router.get("/", response_model=FileListResponse)
def list_files(
    category: Optional[str] = Query(None, description="Filtrer par catégorie (cours, td, tp, examen)"),
    module: Optional[str] = Query(None, description="Filtrer par module"),
    owner_id: Optional[str] = Query(None, description="Filtrer par enseignant"),
    user: dict = Depends(get_current_user),
):
    """
    **Liste les fichiers disponibles** (tous les utilisateurs authentifiés).
    """
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    if category:
        rows = session.execute(
            "SELECT * FROM files WHERE category = %s AND is_public = true ALLOW FILTERING",
            (category,),
        )
    elif module:
        rows = session.execute(
            "SELECT * FROM files WHERE module = %s AND is_public = true ALLOW FILTERING",
            (module,),
        )
    elif owner_id:
        rows = session.execute(
            "SELECT * FROM files WHERE owner_id = %s AND is_public = true ALLOW FILTERING",
            (owner_id,),
        )
    else:
        rows = session.execute(
            "SELECT * FROM files WHERE is_public = true ALLOW FILTERING"
        )

    files = [
        FileMetadata(
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
        )
        for r in rows
    ]

    return FileListResponse(total=len(files), files=files)


@router.get("/my", response_model=FileListResponse)
def my_files(user: dict = Depends(get_current_user)):
    """
    **Mes fichiers uploadés** (tous rôles).
    """
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    rows = session.execute(
        "SELECT * FROM files WHERE owner_id = %s ALLOW FILTERING",
        (user.get("sub"),),
    )

    files = [
        FileMetadata(
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
        )
        for r in rows
    ]

    return FileListResponse(total=len(files), files=files)


@router.get("/{file_id}", response_model=DownloadLinkResponse)
def get_download_link(
    file_id: str,
    expires_hours: int = Query(1, ge=1, le=24, description="Durée de validité du lien en heures"),
    user: dict = Depends(get_current_user),
):
    """
    **Génère un lien de téléchargement sécurisé** accessible directement depuis le navigateur.

    L'URL expire après `expires_hours` heures (défaut : 1h).
    """
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    row = session.execute(
        "SELECT file_id, filename, minio_key, is_public, owner_id FROM files WHERE file_id = %s",
        (uuid.UUID(file_id),),
    ).one()

    if not row:
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    user_roles = user.get("realm_access", {}).get("roles", [])
    is_owner = row.owner_id == user.get("sub")
    is_admin = "admin" in user_roles

    if not row.is_public and not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Accès à ce fichier non autorisé.")

    download_url = get_presigned_download_url(row.minio_key, expires_hours=expires_hours)

    return DownloadLinkResponse(
        file_id=file_id,
        filename=row.filename,
        download_url=download_url,
        expires_in=f"{expires_hours} heure(s)",
    )
