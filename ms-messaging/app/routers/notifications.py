"""
Router : /api/v1/messaging/notifications

Endpoints :
  GET    /                  → mes notifications
  PUT    /{id}/read         → marquer une notif comme lue
  PUT    /read-all          → marquer toutes mes notifs comme lues
  POST   /filiere-event     → [admin] émettre un événement filière
  POST   /schedule-update   → [interne / ms-calendar] MAJ emploi du temps
  POST   /grade-reminder    → [admin] rappel dépôt des notes
  POST   /grades-available  → [interne / ms-notes] notes disponibles
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime

from app.auth import (
    get_current_user, require_admin, require_any,
)
from app.schemas import (
    FiliereEventIn, ScheduleUpdateIn, GradeReminderIn, GradesAvailableIn,
    NotificationListResponse, AckResponse,
)
from app.services.notification_service import (
    get_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    notify_filiere_event,
    notify_schedule_update,
    notify_grade_reminder,
    notify_grades_available,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── Lecture ───────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="Lister mes notifications (les plus récentes en premier)",
)
def list_my_notifications(
    limit: int   = Query(50, ge=1, le=200),
    user:  dict  = Depends(require_any),
):
    notifs = get_notifications(user["sub"], limit=limit)
    return {"total": len(notifs), "notifications": notifs}


@router.put(
    "/read-all",
    response_model=AckResponse,
    summary="Marquer toutes mes notifications comme lues",
)
def read_all(user: dict = Depends(require_any)):
    count = mark_all_notifications_read(user["sub"])
    return {"detail": f"{count} notification(s) marquée(s) comme lues.", "count": count}


@router.put(
    "/{notification_id}/read",
    response_model=AckResponse,
    summary="Marquer une notification spécifique comme lue",
)
def read_one(
    notification_id: str,
    created_at_iso:  str  = Query(..., description="Timestamp ISO 8601 de la notification"),
    user:            dict = Depends(require_any),
):
    try:
        created_at = datetime.fromisoformat(created_at_iso)
    except ValueError:
        raise HTTPException(400, "Format de created_at invalide. Utilisez ISO 8601.")

    ok = mark_notification_read(user["sub"], notification_id, created_at)
    if not ok:
        raise HTTPException(404, "Notification introuvable ou déjà lue.")
    return {"detail": "Notification marquée comme lue."}


# ── Émission (déclencheurs) ───────────────────────────────────────────────────

@router.post(
    "/filiere-event",
    response_model=AckResponse,
    status_code=202,
    summary="[Admin] Notifier tous les membres d'une filière d'un événement",
)
async def emit_filiere_event(
    body:  FiliereEventIn,
    _admin: dict = Depends(require_admin),
):
    """
    Envoie une notification à TOUS les étudiants ET enseignants de la filière.
    """
    count = await notify_filiere_event(body.model_dump())
    return {
        "detail": f"Notification filière envoyée à {count} membre(s).",
        "count":  count,
    }


@router.post(
    "/schedule-update",
    response_model=AckResponse,
    status_code=202,
    summary="[Interne] Notifier un enseignant d'une mise à jour de son emploi du temps",
)
async def emit_schedule_update(
    body:  ScheduleUpdateIn,
    _user: dict = Depends(require_admin),   # appelé par ms-calendar (token service) ou admin
):
    """
    Notifie UNIQUEMENT l'enseignant concerné (changement de salle, séance reprogrammée).
    """
    count = await notify_schedule_update(body.model_dump())
    return {
        "detail": f"Notification envoyée à l'enseignant {body.enseignant_user_id}.",
        "count":  count,
    }


@router.post(
    "/grade-reminder",
    response_model=AckResponse,
    status_code=202,
    summary="[Admin] Rappel aux enseignants pour le dépôt des notes (7 jours avant la date limite)",
)
async def emit_grade_reminder(
    body:   GradeReminderIn,
    _admin: dict = Depends(require_admin),
):
    """
    Notifie les enseignants de la filière qu'ils doivent déposer leurs notes.
    À déclencher une semaine avant la date limite de dépôt.
    """
    count = await notify_grade_reminder(body.model_dump())
    return {
        "detail": f"Rappel dépôt des notes envoyé à {count} enseignant(s).",
        "count":  count,
    }


@router.post(
    "/grades-available",
    response_model=AckResponse,
    status_code=202,
    summary="[Interne] Notifier les membres d'une filière que notes et classement sont disponibles",
)
async def emit_grades_available(
    body:  GradesAvailableIn,
    _user: dict = Depends(require_admin),   # appelé par ms-notes ou admin
):
    """
    Notifie TOUS les étudiants ET enseignants de la filière que les notes
    et le classement sont publiés.
    """
    count = await notify_grades_available(body.model_dump())
    return {
        "detail": f"Notification notes disponibles envoyée à {count} membre(s).",
        "count":  count,
    }
