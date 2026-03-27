from fastapi import APIRouter, Header, HTTPException, Query
from typing import List, Optional
from models.schemas import (CreateNoteRequest, UpdateNoteRequest,
                             NoteResponse, MoyenneResponse, SuccessResponse)
from services.auth_client import require_enseignant_or_admin, require_authenticated
from services.mysql import (create_note, get_notes_by_etudiant, get_all_notes,
                             get_note_by_id, update_note, delete_note, get_moyenne_etudiant)

router = APIRouter(prefix="/notes", tags=["Notes"])


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.post(
    "/",
    response_model=SuccessResponse,
    summary="Saisir une note",
    description="Crée une note pour un étudiant. Réservé aux enseignants et admins."
)
def create_note_endpoint(request: CreateNoteRequest, authorization: str = Header(None)):
    user = require_enseignant_or_admin(get_token(authorization))

    note_id = create_note(
        etudiant_username=request.etudiant_username,
        matiere=request.matiere,
        type_note=request.type.value,
        note=request.note,
        coefficient=request.coefficient,
        semestre=request.semestre,
        annee_universitaire=request.annee_universitaire,
        commentaire=request.commentaire,
        saisi_par=user.get("username", "inconnu")
    )

    return SuccessResponse(message=f"Note {request.note}/20 saisie pour '{request.etudiant_username}' en {request.matiere}")


@router.get(
    "/",
    response_model=List[NoteResponse],
    summary="Toutes les notes",
    description="Retourne toutes les notes. Réservé aux enseignants et admins."
)
def list_all_notes(
    matiere: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    semestre: Optional[str] = Query(None),
    authorization: str = Header(None)
):
    require_enseignant_or_admin(get_token(authorization))
    return get_all_notes(matiere=matiere, type_note=type, semestre=semestre)


@router.get(
    "/mes-notes",
    response_model=List[NoteResponse],
    summary="Mes notes",
    description="Retourne uniquement les notes de l'étudiant connecté."
)
def get_my_notes(
    matiere: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    semestre: Optional[str] = Query(None),
    authorization: str = Header(None)
):
    user = require_authenticated(get_token(authorization))
    username = user.get("username")
    return get_notes_by_etudiant(username, matiere=matiere,
                                  type_note=type, semestre=semestre)


@router.get(
    "/mes-moyennes",
    response_model=List[MoyenneResponse],
    summary="Mes moyennes par matière",
    description="Calcule la moyenne pondérée par matière pour l'étudiant connecté."
)
def get_my_moyennes(
    semestre: Optional[str] = Query(None),
    authorization: str = Header(None)
):
    user = require_authenticated(get_token(authorization))
    username = user.get("username")
    return get_moyenne_etudiant(username, semestre=semestre)


@router.get(
    "/etudiant/{username}",
    response_model=List[NoteResponse],
    summary="Notes d'un étudiant",
    description="Retourne les notes d'un étudiant spécifique. Réservé aux enseignants et admins."
)
def get_student_notes(
    username: str,
    matiere: Optional[str] = Query(None),
    semestre: Optional[str] = Query(None),
    authorization: str = Header(None)
):
    require_enseignant_or_admin(get_token(authorization))
    return get_notes_by_etudiant(username, matiere=matiere, semestre=semestre)


@router.get(
    "/etudiant/{username}/moyennes",
    response_model=List[MoyenneResponse],
    summary="Moyennes d'un étudiant",
    description="Calcule les moyennes d'un étudiant. Réservé aux enseignants et admins."
)
def get_student_moyennes(
    username: str,
    semestre: Optional[str] = Query(None),
    authorization: str = Header(None)
):
    require_enseignant_or_admin(get_token(authorization))
    return get_moyenne_etudiant(username, semestre=semestre)


@router.put(
    "/{note_id}",
    response_model=SuccessResponse,
    summary="Modifier une note"
)
def update_note_endpoint(note_id: int, request: UpdateNoteRequest, authorization: str = Header(None)):
    require_enseignant_or_admin(get_token(authorization))

    note = get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note non trouvée")

    fields = {k: v for k, v in request.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")

    update_note(note_id, fields)
    return SuccessResponse(message=f"Note {note_id} mise à jour")


@router.delete(
    "/{note_id}",
    response_model=SuccessResponse,
    summary="Supprimer une note"
)
def delete_note_endpoint(note_id: int, authorization: str = Header(None)):
    require_enseignant_or_admin(get_token(authorization))

    note = get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note non trouvée")

    delete_note(note_id)
    return SuccessResponse(message=f"Note {note_id} supprimée")