from fastapi import APIRouter, Header, HTTPException, Query
from typing import List, Optional
from models.schemas import CoursResponse, CoursWithFilesResponse
from services.auth_client import require_authenticated
from services.mysql import get_all_cours, get_cours_by_id, search_cours
from services.cassandra import get_files_by_cours

router = APIRouter(prefix="/courses", tags=["Cours"])


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.get(
    "/",
    response_model=List[CoursResponse],
    summary="Liste de tous les cours",
    description="Retourne tous les cours disponibles. Accessible à tous les utilisateurs authentifiés."
)
def list_courses(
    matiere: Optional[str] = Query(None, description="Filtrer par matière"),
    niveau: Optional[str] = Query(None, description="Filtrer par niveau (L1, L2, L3, M1, M2)"),
    authorization: str = Header(None)
):
    require_authenticated(get_token(authorization))
    if matiere or niveau:
        return search_cours(matiere=matiere, niveau=niveau)
    return get_all_cours()


@router.get(
    "/{cours_id}",
    response_model=CoursWithFilesResponse,
    summary="Détails d'un cours avec ses fichiers",
    description="Retourne un cours et la liste de tous ses fichiers uploadés."
)
def get_course_with_files(cours_id: int, authorization: str = Header(None)):
    require_authenticated(get_token(authorization))

    cours = get_cours_by_id(cours_id)
    if not cours:
        raise HTTPException(status_code=404, detail="Cours non trouvé")

    files = get_files_by_cours(cours_id)

    return CoursWithFilesResponse(cours=cours, files=files)