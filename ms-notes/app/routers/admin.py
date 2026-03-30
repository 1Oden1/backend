"""
Router admin — /api/v1/notes/admin
Rôle requis : admin
"""
import json
import logging
from datetime import datetime
from typing import List, Optional

import aio_pika
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.config import settings
from app.database import get_db
from app.events import (
    publish_student_created, publish_student_deleted,
    publish_teacher_created, publish_teacher_deleted,
)
from app.models import DemandeClassement, DemandeReleve, Enseignant, Etudiant, Note
from app.schemas import (
    AckResponse,
    DemandeClassementRead, DemandeReleveRead,
    EnseignantIn, EnseignantRead,
    EtudiantIn, EtudiantRead,
    NoteIn, NoteRead,
    TraiterDemandeIn,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin — Notes"])


# ── Helper ms-calendar ────────────────────────────────────────────────────────

async def _get_elements_for_semestre(semestre_id: int) -> List[dict]:
    """
    Récupère tous les éléments d'un semestre depuis ms-calendar.
    Réponse : {"modules": [{"elements": [{id, coefficient, ...}]}]}
    """
    url = f"{settings.MS_CALENDAR_URL}/api/v1/calendar/internal/semestres/{semestre_id}"
    headers = {}
    if settings.INTERNAL_SERVICE_TOKEN:
        headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        # Aplatir les éléments depuis les modules
        elements = []
        for module in data.get("modules", []):
            elements.extend(module.get("elements", []))
        return elements
    except Exception as exc:
        logger.error("Erreur ms-calendar semestre %d : %s", semestre_id, exc)
        raise HTTPException(502, f"Impossible de joindre ms-calendar : {exc}")


# ── Helper RabbitMQ ───────────────────────────────────────────────────────────



async def _notify_user(user_id: str, notif_type: str, title: str, body_text: str, related_id: str = "") -> None:
    """Envoie une notification directe à un utilisateur via ms-messaging."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # On doit avoir un token service — on utilise le RabbitMQ en fallback
            # si ms-messaging n'est pas joignable, on logue juste l'erreur
            resp = await client.post(
                f"{settings.MS_MESSAGING_URL}/api/v1/messaging/notifications/direct",
                json={
                    "user_id":    user_id,
                    "type":       notif_type,
                    "title":      title,
                    "content":    body_text,
                    "related_id": related_id,
                },
                headers={"Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"},
            )
            if resp.status_code not in (200, 201, 202):
                logger.warning("Notification directe échouée (%d) : %s", resp.status_code, resp.text[:100])
    except Exception as exc:
        logger.warning("Impossible d'envoyer la notification directe à %s : %s", user_id, exc)

async def _publish_event(routing_key: str, payload: dict) -> None:
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL, timeout=5.0)
        async with connection:
            channel  = await connection.channel()
            exchange = await channel.declare_exchange(
                "ent.events", aio_pika.ExchangeType.TOPIC, durable=True,
            )
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
    except Exception as exc:
        logger.error("Erreur RabbitMQ [%s] : %s", routing_key, exc)


# ════════════════════════════════════════════════════════════════════════════
# Étudiants
# ════════════════════════════════════════════════════════════════════════════

@router.post("/etudiants", response_model=EtudiantRead, status_code=201)
async def create_etudiant(
    body: EtudiantIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if db.query(Etudiant).filter(Etudiant.user_id == body.user_id).first():
        raise HTTPException(409, "Étudiant déjà inscrit (user_id en doublon).")
    if db.query(Etudiant).filter(Etudiant.cne == body.cne).first():
        raise HTTPException(409, "CNE déjà utilisé.")
    obj = Etudiant(
        user_id=body.user_id,
        cne=body.cne,
        prenom=body.prenom,
        nom=body.nom,
        calendar_filiere_id=body.calendar_filiere_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    await publish_student_created(obj.user_id, obj.calendar_filiere_id)
    return obj


@router.get("/etudiants", response_model=List[EtudiantRead])
def list_etudiants(
    filiere_id: Optional[int] = Query(None, description="Filtrer par calendar_filiere_id"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    q = db.query(Etudiant)
    if filiere_id:
        q = q.filter(Etudiant.calendar_filiere_id == filiere_id)
    return q.order_by(Etudiant.nom).all()


@router.get("/etudiants/{etudiant_id}", response_model=EtudiantRead)
def get_etudiant(
    etudiant_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.get(Etudiant, etudiant_id)
    if not obj:
        raise HTTPException(404, "Étudiant introuvable.")
    return obj


@router.delete("/etudiants/{etudiant_id}", status_code=204)
async def delete_etudiant(
    etudiant_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.get(Etudiant, etudiant_id)
    if not obj:
        raise HTTPException(404, "Étudiant introuvable.")
    user_id    = obj.user_id
    filiere_id = obj.calendar_filiere_id
    db.delete(obj)
    db.commit()
    await publish_student_deleted(user_id, filiere_id)


@router.put("/etudiants/{etudiant_id}", response_model=EtudiantRead)
async def update_etudiant(
    etudiant_id: int,
    body: EtudiantIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.get(Etudiant, etudiant_id)
    if not obj:
        raise HTTPException(404, "Étudiant introuvable.")
    obj.cne                 = body.cne
    obj.prenom              = body.prenom
    obj.nom                 = body.nom
    obj.calendar_filiere_id = body.calendar_filiere_id
    db.commit()
    db.refresh(obj)
    return obj


# ════════════════════════════════════════════════════════════════════════════
# Enseignants
# ════════════════════════════════════════════════════════════════════════════

@router.post("/enseignants", response_model=EnseignantRead, status_code=201)
async def create_enseignant(
    body: EnseignantIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if db.query(Enseignant).filter(Enseignant.user_id == body.user_id).first():
        raise HTTPException(409, "Enseignant déjà enregistré.")
    obj = Enseignant(
        user_id=body.user_id,
        prenom=body.prenom,
        nom=body.nom,
        calendar_departement_id=body.calendar_departement_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    await publish_teacher_created(obj.user_id)
    return obj


@router.get("/enseignants", response_model=List[EnseignantRead])
def list_enseignants(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return db.query(Enseignant).order_by(Enseignant.nom).all()


@router.get("/enseignants/{enseignant_id}", response_model=EnseignantRead)
def get_enseignant(
    enseignant_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.get(Enseignant, enseignant_id)
    if not obj:
        raise HTTPException(404, "Enseignant introuvable.")
    return obj


@router.delete("/enseignants/{enseignant_id}", status_code=204)
async def delete_enseignant(
    enseignant_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.get(Enseignant, enseignant_id)
    if not obj:
        raise HTTPException(404, "Enseignant introuvable.")
    user_id = obj.user_id
    db.delete(obj)
    db.commit()
    await publish_teacher_deleted(user_id)


@router.put("/enseignants/{enseignant_id}", response_model=EnseignantRead)
async def update_enseignant(
    enseignant_id: int,
    body: EnseignantIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.get(Enseignant, enseignant_id)
    if not obj:
        raise HTTPException(404, "Enseignant introuvable.")
    obj.prenom                  = body.prenom
    obj.nom                     = body.nom
    obj.calendar_departement_id = body.calendar_departement_id
    db.commit()
    db.refresh(obj)
    return obj


# ════════════════════════════════════════════════════════════════════════════
# Notes
# ════════════════════════════════════════════════════════════════════════════

@router.post("/notes", response_model=NoteRead, status_code=201,
             summary="Saisir ou mettre à jour une note (UPSERT)")
def upsert_note(
    body: NoteIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if not db.get(Etudiant, body.etudiant_id):
        raise HTTPException(404, "Étudiant introuvable.")

    existing = db.query(Note).filter(
        Note.etudiant_id         == body.etudiant_id,
        Note.calendar_element_id == body.calendar_element_id,
    ).first()

    if existing:
        existing.note       = body.note
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    note = Note(
        etudiant_id=body.etudiant_id,
        calendar_element_id=body.calendar_element_id,
        note=body.note,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/etudiants/{etudiant_id}/notes", response_model=List[NoteRead])
def get_notes_etudiant(
    etudiant_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if not db.get(Etudiant, etudiant_id):
        raise HTTPException(404, "Étudiant introuvable.")
    return db.query(Note).filter(Note.etudiant_id == etudiant_id).all()


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note introuvable.")
    db.delete(note)
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# Complétude & Publication
# ════════════════════════════════════════════════════════════════════════════

@router.get("/semestres/{semestre_id}/filieres/{filiere_id}/completude",
            summary="Vérifier que toutes les notes sont saisies")
async def check_completude(
    semestre_id: int,
    filiere_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    etudiants = db.query(Etudiant).filter(
        Etudiant.calendar_filiere_id == filiere_id
    ).all()
    if not etudiants:
        raise HTTPException(404, "Aucun étudiant dans cette filière.")

    elements = await _get_elements_for_semestre(semestre_id)
    if not elements:
        raise HTTPException(404, "Aucun élément de module trouvé dans ms-calendar.")

    etudiant_ids  = [e.id for e in etudiants]
    element_ids   = [e["id"] for e in elements]
    total_attendu = len(etudiant_ids) * len(element_ids)
    notes_saisies = db.query(Note).filter(
        Note.etudiant_id.in_(etudiant_ids),
        Note.calendar_element_id.in_(element_ids),
    ).count()
    manquantes = total_attendu - notes_saisies

    return {
        "semestre_id":      semestre_id,
        "filiere_id":       filiere_id,
        "nb_etudiants":     len(etudiants),
        "nb_elements":      len(elements),
        "notes_attendues":  total_attendu,
        "notes_saisies":    notes_saisies,
        "notes_manquantes": manquantes,
        "pret_a_publier":   manquantes == 0,
    }


@router.post("/semestres/{semestre_id}/filieres/{filiere_id}/publier",
             response_model=AckResponse, status_code=202,
             summary="Publier les notes (envoie un événement RabbitMQ)")
async def publier_notes(
    semestre_id: int,
    filiere_id: int,
    force: bool = Query(False, description="Publier même si des notes manquent"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if not force:
        etudiants    = db.query(Etudiant).filter(Etudiant.calendar_filiere_id == filiere_id).all()
        elements     = await _get_elements_for_semestre(semestre_id)
        etudiant_ids = [e.id for e in etudiants]
        element_ids  = [e["id"] for e in elements]
        total        = len(etudiant_ids) * len(element_ids)
        saisies      = db.query(Note).filter(
            Note.etudiant_id.in_(etudiant_ids),
            Note.calendar_element_id.in_(element_ids),
        ).count()
        manquantes = total - saisies
        if manquantes > 0:
            raise HTTPException(409, f"{manquantes} note(s) manquante(s). Utilisez ?force=true.")

    await _publish_event(
        routing_key="grades.available",
        payload={"filiere_id": filiere_id, "semestre_id": semestre_id},
    )
    return {"detail": "Notes publiées. Notification envoyée via RabbitMQ.", "count": 0}


# ════════════════════════════════════════════════════════════════════════════
# Demandes de relevé
# ════════════════════════════════════════════════════════════════════════════

@router.get("/demandes-releve", response_model=List[DemandeReleveRead])
def list_demandes_releve(
    statut: Optional[str] = Query(None, pattern="^(en_attente|approuve|rejete)$"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    q = db.query(DemandeReleve)
    if statut:
        q = q.filter(DemandeReleve.statut == statut)
    return q.order_by(DemandeReleve.demande_le.desc()).all()


@router.patch("/demandes-releve/{demande_id}", response_model=DemandeReleveRead)
async def traiter_releve(
    demande_id: int,
    body: TraiterDemandeIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    demande = db.get(DemandeReleve, demande_id)
    if not demande:
        raise HTTPException(404, "Demande introuvable.")
    if demande.statut != "en_attente":
        raise HTTPException(400, f"Demande déjà traitée ({demande.statut}).")
    demande.statut      = body.statut
    demande.motif_rejet = body.motif_rejet
    demande.traite_le   = datetime.utcnow()
    db.commit()
    db.refresh(demande)

    # Notifier l'étudiant selon le statut
    if body.statut == "approuve":
        await _notify_user(
            user_id    = demande.demandeur_user_id,
            notif_type = "releve_approuve",
            title      = "✅ Relevé de notes approuvé",
            body_text  = f"Votre demande de relevé (semestre #{demande.calendar_semestre_id}) a été approuvée. Vous pouvez le consulter.",
            related_id = str(demande.id),
        )
    elif body.statut == "rejete":
        motif = body.motif_rejet or "Aucun motif précisé."
        await _notify_user(
            user_id    = demande.demandeur_user_id,
            notif_type = "releve_rejete",
            title      = "❌ Relevé de notes refusé",
            body_text  = f"Votre demande de relevé a été refusée. Motif : {motif}",
            related_id = str(demande.id),
        )
    return demande


# ════════════════════════════════════════════════════════════════════════════
# Demandes de classement
# ════════════════════════════════════════════════════════════════════════════

@router.get("/demandes-classement", response_model=List[DemandeClassementRead])
def list_demandes_classement(
    statut: Optional[str] = Query(None, pattern="^(en_attente|approuve|rejete)$"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    q = db.query(DemandeClassement)
    if statut:
        q = q.filter(DemandeClassement.statut == statut)
    return q.order_by(DemandeClassement.demande_le.desc()).all()


@router.patch("/demandes-classement/{demande_id}", response_model=DemandeClassementRead)
async def traiter_classement(
    demande_id: int,
    body: TraiterDemandeIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    demande = db.get(DemandeClassement, demande_id)
    if not demande:
        raise HTTPException(404, "Demande introuvable.")
    if demande.statut != "en_attente":
        raise HTTPException(400, f"Demande déjà traitée ({demande.statut}).")
    demande.statut      = body.statut
    demande.motif_rejet = body.motif_rejet
    demande.traite_le   = datetime.utcnow()
    db.commit()
    db.refresh(demande)

    # Récupérer l'user_id de l'étudiant
    etudiant = db.get(Etudiant, demande.etudiant_id)
    if etudiant:
        if body.statut == "approuve":
            await _notify_user(
                user_id    = etudiant.user_id,
                notif_type = "classement_approuve",
                title      = "🏆 Classement disponible",
                body_text  = f"Votre classement ({demande.type_classement}) pour le semestre #{demande.calendar_semestre_id} est disponible.",
                related_id = str(demande.id),
            )
        elif body.statut == "rejete":
            motif = body.motif_rejet or "Aucun motif précisé."
            await _notify_user(
                user_id    = etudiant.user_id,
                notif_type = "classement_rejete",
                title      = "❌ Demande de classement refusée",
                body_text  = f"Votre demande de classement a été refusée. Motif : {motif}",
                related_id = str(demande.id),
            )
    return demande
