from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from models.schemas import UploadResponse
from services.auth_client import require_enseignant
from services.minio import upload_file
from services.cassandra import save_metadata
from services.mysql import get_cours_by_id
import uuid

router = APIRouter(prefix="/files", tags=["Fichiers"])

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc"
}

MAX_SIZE = 50 * 1024 * 1024  # 50 MB


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload un fichier de cours",
    description="Upload un fichier PDF ou DOCX vers MinIO + métadonnées dans Cassandra."
)
async def upload_course_file(
    cours_id: int = Form(...),
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    user = require_enseignant(get_token(authorization))

    # Vérifier que le cours existe
    cours = get_cours_by_id(cours_id)
    if not cours:
        raise HTTPException(status_code=404, detail="Cours non trouvé")

    # Vérifier le type de fichier
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté. Acceptés: PDF, DOCX"
        )

    # Lire le fichier
    file_data = await file.read()

    # Vérifier la taille
    if len(file_data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 50MB)")

    # Générer un nom unique
    extension = ALLOWED_TYPES[file.content_type]
    unique_filename = f"{uuid.uuid4()}{extension}"

    # Upload vers MinIO
    minio_path = upload_file(file_data, unique_filename, file.content_type)

    # Sauvegarder les métadonnées dans Cassandra
    file_id = save_metadata(
        cours_id=cours_id,
        filename=unique_filename,
        original_name=file.filename,
        content_type=file.content_type,
        size=len(file_data),
        minio_path=minio_path,
        uploaded_by=user.get("username", "inconnu")
    )

    return UploadResponse(
        message="Fichier uploadé avec succès",
        file_id=file_id,
        cours_id=cours_id,
        filename=file.filename,
        size=len(file_data)
    )