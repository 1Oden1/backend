from fastapi import APIRouter, Header, HTTPException
from typing import List
from models.schemas import CreateCoursRequest, CoursResponse, SuccessResponse
from services.auth_client import require_enseignant
from services.mysql import create_cours, get_all_cours, get_cours_by_id

router = APIRouter(prefix="/courses", tags=["Cours"])


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.post(
    "/",
    response_model=SuccessResponse,
    summary="Créer un cours",
    description="Crée un nouveau cours dans MySQL. Réservé aux enseignants."
)
def create_course(request: CreateCoursRequest, authorization: str = Header(None)):
    user = require_enseignant(get_token(authorization))
    enseignant = user.get("username", "inconnu")

    cours_id = create_cours(
        titre=request.titre,
        description=request.description,
        matiere=request.matiere,
        niveau=request.niveau,
        enseignant=enseignant
    )

    return SuccessResponse(message=f"Cours '{request.titre}' créé avec ID {cours_id}")


@router.get(
    "/",
    response_model=List[CoursResponse],
    summary="Liste des cours"
)
def list_courses(authorization: str = Header(None)):
    require_enseignant(get_token(authorization))
    return get_all_cours()


@router.get(
    "/{cours_id}",
    response_model=CoursResponse,
    summary="Détails d'un cours"
)
def get_course(cours_id: int, authorization: str = Header(None)):
    require_enseignant(get_token(authorization))
    cours = get_cours_by_id(cours_id)
    if not cours:
        raise HTTPException(status_code=404, detail="Cours non trouvé")
    return cours