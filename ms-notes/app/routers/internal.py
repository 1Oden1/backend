"""
Router internal — /api/v1/notes/internal
Appels inter-services uniquement (non exposé dans Swagger public).
Routes sans authentification JWT : accessibles uniquement depuis le réseau Docker interne.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Etudiant

router = APIRouter(prefix="/internal", tags=["Internal"], include_in_schema=False)


@router.get("/health")
def internal_health():
    return {"status": "ok", "service": "ms-notes"}


@router.get("/students")
def get_students_of_filiere(
    filiere_id: int = Query(..., description="ID de la filière"),
    db: Session = Depends(get_db),
):
    """Retourne les user_ids des étudiants d'une filière — utilisé par ms-messaging."""
    rows = db.query(Etudiant.user_id).filter(
        Etudiant.calendar_filiere_id == filiere_id
    ).all()
    return {"user_ids": [r.user_id for r in rows]}



@router.get("/student-filiere")
def get_student_filiere(
    user_id: str = Query(..., description="UUID Keycloak de l'étudiant"),
    db: Session = Depends(get_db),
):
    """Retourne la filière d'un étudiant — utilisé par ms-messaging."""
    etudiant = db.query(Etudiant).filter(Etudiant.user_id == user_id).first()
    if not etudiant:
        return {"filiere_id": None}
    return {"filiere_id": etudiant.calendar_filiere_id}
