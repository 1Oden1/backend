"""
Scheduler APScheduler — ms-messaging.

Tâches planifiées :
  - check_grade_deadlines : chaque jour à 08h00
    → interroge ms-notes via HTTP pour obtenir les semestres dont
      date_limite_depot = today + 7 jours
    → envoie automatiquement un rappel aux enseignants de chaque filière concernée

NOTE : ms-messaging ne se connecte plus directement à ent_notes.
       La requête sur les semestres passe par l'endpoint interne de ms-notes.
"""

import logging
import os
from datetime import date, timedelta

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.http_clients import _headers
from app.services.notification_service import notify_grade_reminder

logger = logging.getLogger(__name__)

# ms-calendar est la source de vérité pour date_limite_depot (plus ms-notes)
MS_CALENDAR_URL = os.getenv("MS_CALENDAR_URL", "http://ent_ms_calendar:8000")

_scheduler: AsyncIOScheduler | None = None


async def check_grade_deadlines() -> None:
    """
    Recherche via ms-notes tous les semestres dont la date limite de dépôt
    est exactement dans 7 jours, puis envoie le rappel aux enseignants.
    """
    target_date = date.today() + timedelta(days=7)
    logger.info("[Scheduler] Vérification des deadlines pour : %s", target_date)

    try:
        resp = httpx.get(
            f"{MS_CALENDAR_URL}/api/v1/calendar/internal/semestres-deadline",
            params={"date_limite": target_date.isoformat()},
            headers=_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        rows = resp.json().get("semestres", [])
    except Exception as exc:
        logger.error("[Scheduler] Impossible d'interroger ms-calendar : %s", exc)
        return

    if not rows:
        logger.info("[Scheduler] Aucun semestre à rappeler aujourd'hui.")
        return

    for row in rows:
        semestre_id  = row["id"]
        semestre_nom = row["nom"]
        filiere_id   = row["filiere_id"]

        logger.info(
            "[Scheduler] Rappel dépôt des notes — filière %d, semestre %s",
            filiere_id, semestre_nom,
        )
        try:
            await notify_grade_reminder({
                "filiere_id":     filiere_id,
                "semestre_id":    semestre_id,
                "date_limite":    target_date.isoformat(),
                "jours_restants": 7,
            })
        except Exception as exc:
            logger.error(
                "[Scheduler] Erreur rappel filière %d sem %d : %s",
                filiere_id, semestre_id, exc,
            )


def start_scheduler() -> AsyncIOScheduler:
    """Démarre le scheduler APScheduler et retourne l'instance."""
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Africa/Casablanca")

    _scheduler.add_job(
        check_grade_deadlines,
        trigger=CronTrigger(hour=8, minute=0),
        id="check_grade_deadlines",
        name="Rappel dépôt des notes (J-7)",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info("[Scheduler] Démarré — tâche 'check_grade_deadlines' à 08h00 (Africa/Casablanca).")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Arrêté.")
