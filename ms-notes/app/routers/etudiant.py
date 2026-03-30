"""
Router étudiant — /api/v1/notes/etudiant
Rôle requis : etudiant | delegue
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_student
from app.database import get_db
from app.models import DemandeClassement, DemandeReleve, Etudiant
from app.schemas import (
    DemandeClassementIn, DemandeClassementOut,
    DemandeReleveIn, DemandeReleveOut,
    EtudiantRead,
    MonClassementOut,
    ReleveOut,
    SemestreNotesOut,
)
from app.services import (
    calculer_notes_semestre,
    get_etudiant_by_user_id,
    mon_classement,
)

router = APIRouter(prefix="/api/v1/notes/etudiant", tags=["Étudiant"])


# ── Profil ────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=EtudiantRead,
            summary="Mon profil étudiant")
def mon_profil(
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Profil étudiant introuvable. Contactez l'administration.",
        )
    return etudiant


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.get("/notes/{semestre_id}", response_model=SemestreNotesOut,
            summary="Mes notes pour un semestre")
def mes_notes_semestre(
    semestre_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    return calculer_notes_semestre(db, etudiant, semestre_id)


# ── Demandes de classement ────────────────────────────────────────────────────

@router.get("/mes-demandes-classement", response_model=List[DemandeClassementOut],
            summary="Toutes mes demandes de classement")
def mes_demandes_classement(
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    return (
        db.query(DemandeClassement)
        .filter(DemandeClassement.etudiant_id == etudiant.id)
        .order_by(DemandeClassement.demande_le.desc())
        .all()
    )


@router.post("/demandes-classement", response_model=DemandeClassementOut,
             status_code=status.HTTP_201_CREATED,
             summary="Demander mon classement")
def demander_classement(
    body: DemandeClassementIn,
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    if body.type_classement not in ("filiere", "departement"):
        raise HTTPException(400, "type_classement doit être 'filiere' ou 'departement'.")

    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")

    existant = (
        db.query(DemandeClassement)
        .filter(
            DemandeClassement.etudiant_id == etudiant.id,
            DemandeClassement.calendar_semestre_id == body.calendar_semestre_id,
            DemandeClassement.type_classement == body.type_classement,
            DemandeClassement.statut == "en_attente",
        )
        .first()
    )
    if existant:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Une demande de classement identique est déjà en attente.",
        )

    demande = DemandeClassement(
        etudiant_id=etudiant.id,
        calendar_semestre_id=body.calendar_semestre_id,
        type_classement=body.type_classement,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return demande


@router.get("/demandes-classement/{demande_id}", response_model=DemandeClassementOut,
            summary="Statut d'une demande de classement")
def statut_demande_classement(
    demande_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    demande = db.query(DemandeClassement).filter(
        DemandeClassement.id == demande_id,
        DemandeClassement.etudiant_id == etudiant.id,
    ).first()
    if not demande:
        raise HTTPException(404, "Demande introuvable.")
    return demande


@router.get("/classements/{demande_id}", response_model=MonClassementOut,
            summary="Résultat de mon classement (après approbation)")
def resultat_classement(
    demande_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    demande = db.query(DemandeClassement).filter(
        DemandeClassement.id == demande_id,
        DemandeClassement.etudiant_id == etudiant.id,
    ).first()
    if not demande:
        raise HTTPException(404, "Demande introuvable.")
    if demande.statut == "en_attente":
        raise HTTPException(202, "Demande en attente de validation par l'admin.")
    if demande.statut == "rejete":
        raise HTTPException(403, f"Demande rejetée : {demande.motif_rejet or 'sans motif'}.")
    return mon_classement(db, etudiant, demande)


# ── Demandes de relevé ────────────────────────────────────────────────────────

@router.get("/mes-demandes-releve", response_model=List[DemandeReleveOut],
            summary="Toutes mes demandes de relevé")
def mes_demandes_releve(
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    return (
        db.query(DemandeReleve)
        .filter(DemandeReleve.etudiant_id == etudiant.id)
        .order_by(DemandeReleve.demande_le.desc())
        .all()
    )


@router.post("/demandes-releve", response_model=DemandeReleveOut,
             status_code=status.HTTP_201_CREATED,
             summary="Demander mon relevé de notes")
def demander_releve(
    body: DemandeReleveIn,
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")

    existant = (
        db.query(DemandeReleve)
        .filter(
            DemandeReleve.etudiant_id == etudiant.id,
            DemandeReleve.calendar_semestre_id == body.calendar_semestre_id,
            DemandeReleve.statut == "en_attente",
        )
        .first()
    )
    if existant:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Une demande de relevé est déjà en attente pour ce semestre.",
        )

    demande = DemandeReleve(
        demandeur_user_id=user["sub"],
        role_demandeur="etudiant",
        etudiant_id=etudiant.id,
        calendar_semestre_id=body.calendar_semestre_id,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return demande


@router.get("/demandes-releve/{demande_id}", response_model=DemandeReleveOut,
            summary="Statut d'une demande de relevé")
def statut_demande_releve(
    demande_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    demande = db.query(DemandeReleve).filter(
        DemandeReleve.id == demande_id,
        DemandeReleve.etudiant_id == etudiant.id,
    ).first()
    if not demande:
        raise HTTPException(404, "Demande introuvable.")
    return demande


@router.get("/releves/{demande_id}", response_model=ReleveOut,
            summary="Récupérer mon relevé de notes (après approbation)")
def telecharger_releve(
    demande_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_student),
):
    etudiant = get_etudiant_by_user_id(db, user["sub"])
    if not etudiant:
        raise HTTPException(404, "Profil étudiant introuvable.")
    demande = db.query(DemandeReleve).filter(
        DemandeReleve.id == demande_id,
        DemandeReleve.etudiant_id == etudiant.id,
    ).first()
    if not demande:
        raise HTTPException(404, "Demande introuvable.")
    if demande.statut == "en_attente":
        raise HTTPException(202, "Demande en attente de validation par l'admin.")
    if demande.statut == "rejete":
        raise HTTPException(403, f"Demande rejetée : {demande.motif_rejet or 'sans motif'}.")

    notes = calculer_notes_semestre(db, etudiant, demande.calendar_semestre_id)
    return ReleveOut(
        demande_id=demande.id,
        etudiant_cne=etudiant.cne,
        etudiant_nom=f"{etudiant.prenom} {etudiant.nom}",
        notes=notes,
    )
