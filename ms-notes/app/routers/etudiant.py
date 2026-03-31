"""
Router étudiant — /api/v1/notes/etudiant
Rôle requis : etudiant | delegue
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_student
from app.database import get_db
from app.models import DemandeClassement, DemandeReleve, Enseignant, Etudiant
from app.schemas import (
    DemandeClassementIn, DemandeClassementOut,
    DemandeReleveIn, DemandeReleveOut,
    EtudiantRead,
    MonClassementOut,
    ReleveOut,
    SemestreNotesOut,
)
from app.services import (
    _cal_get,
    calculer_notes_semestre,
    get_etudiant_by_user_id,
    mon_classement,
)

router = APIRouter(prefix="/api/v1/notes/etudiant", tags=["Étudiant"])


# ── Enseignants de ma filière (pour le chat) ──────────────────────────────────

@router.get("/enseignants-filiere",
            summary="Enseignants de MA filière (pour le chat délégué)")
def enseignants_ma_filiere(
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    """
    Retourne les enseignants ayant au moins une séance dans la filière du délégué.
    Source : ms-calendar/internal — même source que check_chat_permission dans ms-messaging.
    Garantit que la liste affichée = la liste autorisée par le backend.
    """
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    if not etudiant.calendar_filiere_id:
        raise HTTPException(404, "Filière non configurée pour cet étudiant.")
    try:
        data = _cal_get(f"filieres/{etudiant.calendar_filiere_id}/enseignants")
        enseignants = data.get("enseignants", [])
    except Exception:
        raise HTTPException(502, "Impossible de récupérer les enseignants depuis ms-calendar.")
    return [
        {
            "user_id": e["user_id"],
            "prenom":  e.get("prenom", ""),
            "nom":     e.get("nom", ""),
            "peut_chatter": bool(e.get("user_id")),
        }
        for e in enseignants
        if e.get("user_id")  # uniquement les enseignants avec un compte Keycloak lié
    ]


# ── Profil ────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=EtudiantRead, summary="Mon profil étudiant")
def mon_profil(db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    return e


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.get("/notes/{semestre_id}", response_model=SemestreNotesOut)
def mes_notes(semestre_id: int, db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    return calculer_notes_semestre(db, e, semestre_id)


# ── Demandes de relevé ────────────────────────────────────────────────────────

@router.get("/mes-demandes-releve", response_model=List[DemandeReleveOut])
def mes_demandes_releve(db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    return db.query(DemandeReleve).filter(DemandeReleve.etudiant_id == e.id).order_by(DemandeReleve.demande_le.desc()).all()


@router.post("/demandes-releve", response_model=DemandeReleveOut, status_code=status.HTTP_201_CREATED)
def demander_releve(body: DemandeReleveIn, db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    existant = db.query(DemandeReleve).filter(DemandeReleve.etudiant_id == e.id, DemandeReleve.calendar_semestre_id == body.calendar_semestre_id, DemandeReleve.statut == "en_attente").first()
    if existant:
        raise HTTPException(409, "Une demande est déjà en attente pour ce semestre.")
    d = DemandeReleve(demandeur_user_id=user["sub"], role_demandeur="etudiant", etudiant_id=e.id, calendar_semestre_id=body.calendar_semestre_id)
    db.add(d); db.commit(); db.refresh(d)
    return d


@router.get("/demandes-releve/{demande_id}", response_model=DemandeReleveOut)
def statut_releve(demande_id: int, db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    d = db.query(DemandeReleve).filter(DemandeReleve.id == demande_id, DemandeReleve.etudiant_id == e.id).first()
    if not d:
        raise HTTPException(404, "Demande introuvable.")
    return d


@router.get("/releves/{demande_id}", response_model=ReleveOut)
def telecharger_releve(demande_id: int, db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    d = db.query(DemandeReleve).filter(DemandeReleve.id == demande_id, DemandeReleve.etudiant_id == e.id).first()
    if not d:
        raise HTTPException(404, "Demande introuvable.")
    if d.statut == "en_attente":
        raise HTTPException(202, "En attente de validation.")
    if d.statut == "rejete":
        raise HTTPException(403, f"Rejetée : {d.motif_rejet or 'sans motif'}.")
    return ReleveOut(demande_id=d.id, etudiant_cne=e.cne, etudiant_nom=f"{e.prenom} {e.nom}", notes=calculer_notes_semestre(db, e, d.calendar_semestre_id))


# ── Demandes de classement ────────────────────────────────────────────────────

@router.get("/mes-demandes-classement", response_model=List[DemandeClassementOut])
def mes_demandes_classement(db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    return db.query(DemandeClassement).filter(DemandeClassement.etudiant_id == e.id).order_by(DemandeClassement.demande_le.desc()).all()


@router.post("/demandes-classement", response_model=DemandeClassementOut, status_code=status.HTTP_201_CREATED)
def demander_classement(body: DemandeClassementIn, db: Session = Depends(get_db), user: dict = Depends(require_student)):
    if body.type_classement not in ("filiere", "departement"):
        raise HTTPException(400, "type_classement doit être 'filiere' ou 'departement'.")
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    existant = db.query(DemandeClassement).filter(DemandeClassement.etudiant_id == e.id, DemandeClassement.calendar_semestre_id == body.calendar_semestre_id, DemandeClassement.type_classement == body.type_classement, DemandeClassement.statut == "en_attente").first()
    if existant:
        raise HTTPException(409, "Une demande identique est déjà en attente.")
    d = DemandeClassement(etudiant_id=e.id, calendar_semestre_id=body.calendar_semestre_id, type_classement=body.type_classement)
    db.add(d); db.commit(); db.refresh(d)
    return d


@router.get("/demandes-classement/{demande_id}", response_model=DemandeClassementOut)
def statut_classement(demande_id: int, db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    d = db.query(DemandeClassement).filter(DemandeClassement.id == demande_id, DemandeClassement.etudiant_id == e.id).first()
    if not d:
        raise HTTPException(404, "Demande introuvable.")
    return d


@router.get("/classements/{demande_id}", response_model=MonClassementOut)
def resultat_classement(demande_id: int, db: Session = Depends(get_db), user: dict = Depends(require_student)):
    e = get_etudiant_by_user_id(db, user["sub"])
    if not e:
        raise HTTPException(404, "Profil étudiant introuvable.")
    d = db.query(DemandeClassement).filter(DemandeClassement.id == demande_id, DemandeClassement.etudiant_id == e.id).first()
    if not d:
        raise HTTPException(404, "Demande introuvable.")
    if d.statut == "en_attente":
        raise HTTPException(202, "En attente de validation.")
    if d.statut == "rejete":
        raise HTTPException(403, f"Rejetée : {d.motif_rejet or 'sans motif'}.")
    return mon_classement(db, e, d)
