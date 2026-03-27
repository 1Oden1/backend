from fastapi import APIRouter, Header, HTTPException, Query
from typing import List, Optional
from models.schemas import CreateEvenementRequest, UpdateEvenementRequest, EvenementResponse, SuccessResponse
from services.auth_client import require_authenticated, require_enseignant_or_admin
from services.mysql import (create_evenement, get_all_evenements,
                             get_evenement_by_id, update_evenement, delete_evenement)

router = APIRouter(prefix="/calendar", tags=["Calendrier"])


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.post(
    "/",
    response_model=SuccessResponse,
    summary="Créer un événement",
    description="Crée un événement (cours, examen, événement général). Réservé aux enseignants et admins."
)
def create_event(request: CreateEvenementRequest, authorization: str = Header(None)):
    user = require_enseignant_or_admin(get_token(authorization))

    if request.date_fin <= request.date_debut:
        raise HTTPException(status_code=400, detail="date_fin doit être après date_debut")

    evt_id = create_evenement(
        titre=request.titre,
        description=request.description,
        type_evt=request.type.value,
        date_debut=request.date_debut,
        date_fin=request.date_fin,
        lieu=request.lieu,
        filiere=request.filiere,
        niveau=request.niveau,
        cree_par=user.get("username", "inconnu")
    )

    return SuccessResponse(message=f"Événement '{request.titre}' créé avec ID {evt_id}")


@router.get(
    "/",
    response_model=List[EvenementResponse],
    summary="Liste des événements",
    description="Retourne tous les événements. Filtrable par type, niveau, filière."
)
def list_events(
    type: Optional[str] = Query(None, description="cours | examen | evenement"),
    niveau: Optional[str] = Query(None, description="L1, L2, L3, M1, M2"),
    filiere: Optional[str] = Query(None, description="Filière"),
    authorization: str = Header(None)
):
    require_authenticated(get_token(authorization))
    return get_all_evenements(type_evt=type, niveau=niveau, filiere=filiere)


@router.get(
    "/{evt_id}",
    response_model=EvenementResponse,
    summary="Détails d'un événement"
)
def get_event(evt_id: int, authorization: str = Header(None)):
    require_authenticated(get_token(authorization))
    evt = get_evenement_by_id(evt_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return evt


@router.put(
    "/{evt_id}",
    response_model=SuccessResponse,
    summary="Modifier un événement"
)
def update_event(evt_id: int, request: UpdateEvenementRequest, authorization: str = Header(None)):
    require_enseignant_or_admin(get_token(authorization))

    evt = get_evenement_by_id(evt_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Événement non trouvé")

    fields = {k: v for k, v in request.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")

    # Convertir l'enum en string si présent
    if "type" in fields:
        fields["type"] = fields["type"].value

    update_evenement(evt_id, fields)
    return SuccessResponse(message=f"Événement {evt_id} mis à jour")


@router.delete(
    "/{evt_id}",
    response_model=SuccessResponse,
    summary="Supprimer un événement"
)
def delete_event(evt_id: int, authorization: str = Header(None)):
    require_enseignant_or_admin(get_token(authorization))

    evt = get_evenement_by_id(evt_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Événement non trouvé")

    delete_evenement(evt_id)
    return SuccessResponse(message=f"Événement {evt_id} supprimé")