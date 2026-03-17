"""
Service de notifications — ent_messaging.

Règles métier :
  - Événement filière          → TOUS les étudiants ET tous les enseignants de la filière
  - Mise à jour emploi du temps → UNIQUEMENT l'enseignant concerné
  - Rappel dépôt des notes      → les enseignants de la filière (1 semaine avant la date limite)
  - Notes/classement disponibles→ étudiants ET enseignants de la filière
"""

import uuid
import logging
from datetime import datetime, timezone
from cassandra.query import SimpleStatement

from app.database_cassandra import get_session
from app.config import settings

logger = logging.getLogger(__name__)


# ── Helpers Cassandra ─────────────────────────────────────────────────────────

def _insert_notification(
    recipient_id: str,
    notif_type:   str,
    title:        str,
    content:      str,
    related_id:   str | None = None,
) -> None:
    """Insère une notification pour un seul destinataire."""
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    session.execute(
        """
        INSERT INTO notifications
               (recipient_id, created_at, notification_id, type, title, content, related_id, is_read)
        VALUES (%s, %s, %s, %s, %s, %s, %s, false)
        """,
        (
            recipient_id,
            datetime.now(timezone.utc),
            uuid.uuid4(),
            notif_type,
            title,
            content,
            related_id or "",
        ),
    )


def _bulk_notify(
    recipients: list[str],
    notif_type: str,
    title:      str,
    content:    str,
    related_id: str | None = None,
) -> int:
    """Envoie la même notification à une liste de destinataires. Retourne le nombre envoyé."""
    count = 0
    for uid in recipients:
        try:
            _insert_notification(uid, notif_type, title, content, related_id)
            count += 1
        except Exception as exc:
            logger.error("Erreur insertion notif pour %s : %s", uid, exc)
    return count


# ── Handlers RabbitMQ (appelables aussi directement via REST) ─────────────────

async def notify_filiere_event(payload: dict) -> int:
    """
    Payload attendu : {"filiere_id": int, "title": str, "content": str}
    Destinataires   : étudiants + enseignants de la filière.
    """
    from app.http_clients import get_students_of_filiere, get_teachers_of_filiere

    filiere_id = payload["filiere_id"]
    title      = payload["title"]
    content    = payload["content"]
    related_id = str(filiere_id)

    recipients = list({
        *get_students_of_filiere(filiere_id),
        *get_teachers_of_filiere(filiere_id),
    })

    count = _bulk_notify(recipients, "filiere_event", title, content, related_id)
    logger.info("notify_filiere_event — filière %s → %d notifs envoyées", filiere_id, count)
    return count


async def notify_schedule_update(payload: dict) -> int:
    """
    Payload attendu : {
        "enseignant_user_id": str,
        "title": str,
        "content": str,
        "seance_id": int (optionnel)
    }
    Destinataire : UNIQUEMENT l'enseignant concerné.
    """
    uid       = payload["enseignant_user_id"]
    title     = payload["title"]
    content   = payload["content"]
    seance_id = str(payload.get("seance_id", ""))

    try:
        _insert_notification(uid, "schedule_update", title, content, seance_id)
        logger.info("notify_schedule_update → enseignant %s notifié", uid)
        return 1
    except Exception as exc:
        logger.error("Erreur notify_schedule_update : %s", exc)
        return 0


async def notify_grade_reminder(payload: dict) -> int:
    """
    Payload attendu : {
        "filiere_id": int,
        "semestre_id": int,
        "date_limite": str,   # "YYYY-MM-DD"
        "jours_restants": int
    }
    Destinataires : enseignants de la filière (une semaine avant la date limite).
    """
    from app.http_clients import get_teachers_of_filiere, get_filiere_name

    filiere_id      = payload["filiere_id"]
    semestre_id     = payload["semestre_id"]
    date_limite     = payload["date_limite"]
    jours_restants  = payload["jours_restants"]
    filiere_nom     = get_filiere_name(filiere_id)

    title   = f"Rappel : dépôt des notes — {filiere_nom}"
    content = (
        f"Vous avez {jours_restants} jour(s) restant(s) pour déposer les notes "
        f"du semestre {semestre_id} de la filière {filiere_nom}. "
        f"Date limite : {date_limite}."
    )
    related_id = f"{filiere_id}:{semestre_id}"

    teachers = get_teachers_of_filiere(filiere_id)
    count    = _bulk_notify(teachers, "grade_reminder", title, content, related_id)
    logger.info("notify_grade_reminder — filière %s → %d enseignants notifiés", filiere_id, count)
    return count


async def notify_grades_available(payload: dict) -> int:
    """
    Payload attendu : {"filiere_id": int, "semestre_id": int}
    Destinataires   : étudiants + enseignants de la filière.
    """
    from app.http_clients import (
        get_students_of_filiere, get_teachers_of_filiere, get_filiere_name,
    )

    filiere_id  = payload["filiere_id"]
    semestre_id = payload["semestre_id"]
    filiere_nom = get_filiere_name(filiere_id)

    title   = f"Notes et classement disponibles — {filiere_nom}"
    content = (
        f"Les notes et le classement du semestre {semestre_id} "
        f"de la filière {filiere_nom} sont maintenant disponibles."
    )
    related_id = f"{filiere_id}:{semestre_id}"

    recipients = list({
        *get_students_of_filiere(filiere_id),
        *get_teachers_of_filiere(filiere_id),
    })

    count = _bulk_notify(recipients, "grades_available", title, content, related_id)
    logger.info("notify_grades_available — filière %s → %d notifs envoyées", filiere_id, count)
    return count


# ── Notification de nouveau message (appelée par le service chat) ─────────────

def notify_new_message(
    recipient_id:    str,
    sender_name:     str,
    conversation_id: str,
    preview:         str,
) -> None:
    """Notifie un utilisateur de la réception d'un nouveau message."""
    title   = f"Nouveau message de {sender_name}"
    content = preview[:120] + ("…" if len(preview) > 120 else "")
    try:
        _insert_notification(recipient_id, "new_message", title, content, conversation_id)
    except Exception as exc:
        logger.error("Erreur notify_new_message pour %s : %s", recipient_id, exc)


# ── Lecture des notifications ─────────────────────────────────────────────────

def get_notifications(recipient_id: str, limit: int = 50) -> list[dict]:
    """Retourne les [limit] dernières notifications d'un utilisateur."""
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    rows = session.execute(
        SimpleStatement(
            "SELECT notification_id, type, title, content, related_id, is_read, created_at "
            "FROM notifications WHERE recipient_id = %s LIMIT %s",
            fetch_size=limit,
        ),
        (recipient_id, limit),
    )
    return [
        {
            "notification_id": str(r.notification_id),
            "type":            r.type,
            "title":           r.title,
            "content":         r.content,
            "related_id":      r.related_id,
            "is_read":         r.is_read,
            "created_at":      r.created_at,
        }
        for r in rows
    ]


def mark_notification_read(recipient_id: str, notification_id: str, created_at: datetime) -> bool:
    """Marque une notification comme lue."""
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    try:
        session.execute(
            """
            UPDATE notifications SET is_read = true
            WHERE recipient_id = %s AND created_at = %s AND notification_id = %s
            """,
            (recipient_id, created_at, uuid.UUID(notification_id)),
        )
        return True
    except Exception as exc:
        logger.error("Erreur mark_notification_read : %s", exc)
        return False


def mark_all_notifications_read(recipient_id: str) -> int:
    """
    Marque toutes les notifications non lues d'un utilisateur comme lues.
    Retourne le nombre de notifications mises à jour.
    """
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    rows = session.execute(
        "SELECT created_at, notification_id FROM notifications "
        "WHERE recipient_id = %s AND is_read = false ALLOW FILTERING",
        (recipient_id,),
    )
    count = 0
    for r in rows:
        try:
            session.execute(
                """
                UPDATE notifications SET is_read = true
                WHERE recipient_id = %s AND created_at = %s AND notification_id = %s
                """,
                (recipient_id, r.created_at, r.notification_id),
            )
            count += 1
        except Exception as exc:
            logger.error("Erreur mark_all : %s", exc)
    return count
