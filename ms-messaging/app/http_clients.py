"""
http_clients.py — ms-messaging

Remplace database_mysql.py.
Toutes les informations sur les étudiants/enseignants/filières sont
obtenues via les endpoints internes des microservices dédiés :
  - ms-notes  → /api/v1/notes/internal/...
  - ms-calendar → /api/v1/calendar/internal/...

Cela garantit que ms-messaging ne se connecte à AUCUNE base externe.
Il possède uniquement ent_messaging (Cassandra).
"""

import logging
import os

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

MS_NOTES_URL    = os.getenv("MS_NOTES_URL",    "http://ent_ms_notes:8000")
MS_CALENDAR_URL = os.getenv("MS_CALENDAR_URL", "http://ent_ms_calendar:8000")


def _get_service_token() -> str:
    """Obtient un token Keycloak client_credentials pour les appels inter-services."""
    try:
        resp = httpx.post(
            f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
            "/protocol/openid-connect/token",
            data={
                "client_id":     settings.KEYCLOAK_CLIENT_ID,
                "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET", ""),
                "grant_type":    "client_credentials",
            },
            timeout=3.0,
        )
        resp.raise_for_status()
        return resp.json().get("access_token", "")
    except Exception as exc:
        logger.warning("_get_service_token : %s", exc)
        return ""


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_service_token()}"}


# ── ms-notes/internal ─────────────────────────────────────────────────────────

def get_filiere_id_of_student(user_id: str) -> int | None:
    """Retourne le filiere_id d'un étudiant à partir de son user_id Keycloak."""
    try:
        resp = httpx.get(
            f"{MS_NOTES_URL}/api/v1/notes/internal/student-filiere",
            params={"user_id": user_id},
            headers=_headers(),
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("filiere_id")
    except Exception as exc:
        logger.error("get_filiere_id_of_student(%s) : %s", user_id, exc)
        return None


def get_students_of_filiere(filiere_id: int) -> list[str]:
    """Retourne les user_ids des étudiants d'une filière (via ms-notes)."""
    try:
        resp = httpx.get(
            f"{MS_NOTES_URL}/api/v1/notes/internal/students",
            params={"filiere_id": filiere_id},
            headers=_headers(),
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("user_ids", [])
    except Exception as exc:
        logger.error("get_students_of_filiere(%s) : %s", filiere_id, exc)
        return []


def get_all_teachers_user_ids() -> list[str]:
    """Retourne les user_ids de tous les enseignants (via ms-notes)."""
    try:
        resp = httpx.get(
            f"{MS_NOTES_URL}/api/v1/notes/internal/teachers",
            headers=_headers(),
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("user_ids", [])
    except Exception as exc:
        logger.error("get_all_teachers_user_ids : %s", exc)
        return []


# ── ms-calendar/internal ──────────────────────────────────────────────────────

def get_teachers_of_filiere(filiere_id: int) -> list[str]:
    """Retourne les user_ids des enseignants ayant des séances dans la filière (via ms-calendar)."""
    try:
        resp = httpx.get(
            f"{MS_CALENDAR_URL}/api/v1/calendar/internal/filieres/{filiere_id}/enseignants",
            headers=_headers(),
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("user_ids", [])
    except Exception as exc:
        logger.error("get_teachers_of_filiere(%s) : %s", filiere_id, exc)
        return []


def get_filiere_name(filiere_id: int) -> str:
    """Retourne le nom d'une filière (via ms-calendar)."""
    try:
        resp = httpx.get(
            f"{MS_CALENDAR_URL}/api/v1/calendar/internal/filieres/{filiere_id}/nom",
            headers=_headers(),
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("nom", f"Filière #{filiere_id}")
    except Exception as exc:
        logger.error("get_filiere_name(%s) : %s", filiere_id, exc)
        return f"Filière #{filiere_id}"


# Alias de compatibilité (utilisé dans notification_service.py)
get_teachers_of_filiere_for_notes = get_teachers_of_filiere
