"""
Router enseignant — /api/v1/notes/enseignant
Rôle requis : enseignant
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_teacher
from app.database import get_db
from app.models import DemandeReleve, Etudiant
from app.schemas import (
    ClassementCompletOut,
    DemandeReleve_EnseignantIn, DemandeReleveOut,
    ReleveOut,
)
from app.services import (
    calculer_notes_semestre,
    classement_departement,
    classement_filiere,
)

router = APIRouter(prefix="/api/v1/notes/enseignant", tags=["Enseignant"])


# ── Classements ───────────────────────────────────────────────────────────────

@router.get("/classements/filiere/{filiere_id}/semestre/{semestre_id}",
            response_model=ClassementCompletOut,
            summary="Classement complet des étudiants d'une filière")
def voir_classement_filiere(
    filiere_id: int,
    semestre_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher),
):
    return classement_filiere(db, filiere_id, semestre_id)


@router.get("/classements/departement/{departement_id}/semestre/{semestre_id}",
            response_model=ClassementCompletOut,
            summary="Classement complet des étudiants d'un département")
def voir_classement_departement(
    departement_id: int,
    semestre_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher),
):
    return classement_departement(db, departement_id, semestre_id)


# ── Demandes de relevé ────────────────────────────────────────────────────────

@router.post("/demandes-releve", response_model=DemandeReleveOut,
             status_code=status.HTTP_201_CREATED,
             summary="Faire une demande de relevé pour un étudiant")
def demander_releve_etudiant(
    body: DemandeReleve_EnseignantIn,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher),
):
    etudiant = db.get(Etudiant, body.etudiant_id)
    if not etudiant:
        raise HTTPException(404, "Étudiant cible introuvable.")

    existant = db.query(DemandeReleve).filter(
        DemandeReleve.demandeur_user_id    == user["sub"],
        DemandeReleve.etudiant_id          == body.etudiant_id,
        DemandeReleve.calendar_semestre_id == body.calendar_semestre_id,
        DemandeReleve.statut               == "en_attente",
    ).first()
    if existant:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Une demande pour cet étudiant est déjà en attente.")

    demande = DemandeReleve(
        demandeur_user_id=user["sub"],
        role_demandeur="enseignant",
        etudiant_id=body.etudiant_id,
        calendar_semestre_id=body.calendar_semestre_id,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return demande


@router.get("/mes-demandes-releve", response_model=List[DemandeReleveOut],
            summary="Toutes mes demandes de relevé (en tant qu'enseignant)")
def mes_demandes_releve_enseignant(
    db:   Session = Depends(get_db),
    user: dict    = Depends(require_teacher),
):
    """Liste toutes les demandes de relevé soumises par cet enseignant."""
    return db.query(DemandeReleve).filter(
        DemandeReleve.demandeur_user_id == user["sub"]
    ).order_by(DemandeReleve.demande_le.desc()).all()


@router.get("/demandes-releve/{demande_id}", response_model=DemandeReleveOut,
            summary="Statut d'une demande de relevé")
def statut_demande(
    demande_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher),
):
    demande = db.query(DemandeReleve).filter(DemandeReleve.id == demande_id).first()
    if not demande or demande.demandeur_user_id != user["sub"]:
        raise HTTPException(404, "Demande introuvable.")
    return demande


@router.get("/releves/{demande_id}", response_model=ReleveOut,
            summary="Récupérer le relevé d'un étudiant (après approbation)")
def telecharger_releve_etudiant(
    demande_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_teacher),
):
    demande = db.query(DemandeReleve).filter(DemandeReleve.id == demande_id).first()
    if not demande or demande.demandeur_user_id != user["sub"]:
        raise HTTPException(404, "Demande introuvable.")
    if demande.statut == "en_attente":
        raise HTTPException(202, "Demande en attente de validation par l'admin.")
    if demande.statut == "rejete":
        raise HTTPException(403, f"Demande rejetée : {demande.motif_rejet or 'sans motif'}.")

    etudiant = db.get(Etudiant, demande.etudiant_id)
    notes    = calculer_notes_semestre(db, etudiant, demande.calendar_semestre_id)
    return ReleveOut(
        demande_id=demande.id,
        etudiant_cne=etudiant.cne,
        etudiant_nom=f"{etudiant.prenom} {etudiant.nom}",
        notes=notes,
    )
