"""
http_clients.py — ms-messaging

Appels inter-services vers ms-notes /internal et ms-calendar /internal.
Ces routes n'ont pas d'authentification JWT (réseau Docker privé uniquement).
"""

import logging
import os
import httpx

logger = logging.getLogger(__name__)

MS_NOTES_URL    = os.getenv("MS_NOTES_URL",    "http://ent_ms_notes:8000")
MS_CALENDAR_URL = os.getenv("MS_CALENDAR_URL", "http://ent_ms_calendar:8000")


# ── ms-notes/internal ─────────────────────────────────────────────────────────

def get_filiere_id_of_student(user_id: str) -> int | None:
    """Retourne le filiere_id d'un étudiant à partir de son user_id Keycloak."""
    try:
        resp = httpx.get(
            f"{MS_NOTES_URL}/api/v1/notes/internal/student-filiere",
            params={"user_id": user_id},
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("filiere_id")
    except Exception as exc:
        logger.error("get_filiere_id_of_student(%s) : %s", user_id, exc)
        return None


def get_students_of_filiere(filiere_id: int) -> list[str]:
    """Retourne les user_ids des étudiants d'une filière (via ms-notes /internal)."""
    try:
        resp = httpx.get(
            f"{MS_NOTES_URL}/api/v1/notes/internal/students",
            params={"filiere_id": filiere_id},
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("user_ids", [])
    except Exception as exc:
        logger.error("get_students_of_filiere(%s) : %s", filiere_id, exc)
        return []


def get_all_teachers_user_ids() -> list[str]:
    """Retourne les user_ids de tous les enseignants.
    Essaie ms-notes /internal/teachers d'abord, puis ms-calendar comme fallback."""    # Source 1 : ms-notes (enseignants inscrits pour les notes)
    try:
        resp = httpx.get(
            f"{MS_NOTES_URL}/api/v1/notes/internal/teachers",
            timeout=5.0,
        )
        if resp.is_success:
            ids = resp.json().get("user_ids", [])
            if ids:
                return ids
    except Exception as exc:
        logger.warning("get_all_teachers_user_ids ms-notes : %s", exc)

    # Fallback : ms-calendar (enseignants avec user_id Keycloak)
    try:
        resp = httpx.get(
            f"{MS_CALENDAR_URL}/api/v1/calendar/internal/enseignants",
            timeout=5.0,
        )
        if resp.is_success:
            enseignants = resp.json().get("enseignants", [])
            ids = [e["user_id"] for e in enseignants if e.get("user_id")]
            return ids
    except Exception as exc:
        logger.error("get_all_teachers_user_ids ms-calendar : %s", exc)
    return []


# ── ms-calendar/internal ──────────────────────────────────────────────────────

def get_teachers_of_filiere(filiere_id: int) -> list[str]:
    """
    Retourne les user_ids des enseignants ayant des séances dans la filière.
    La route ms-calendar retourne {"enseignants": [{id, user_id, nom, prenom, email}]}.
    On extrait uniquement les user_ids non-null.
    """
    try:
        resp = httpx.get(
            f"{MS_CALENDAR_URL}/api/v1/calendar/internal/filieres/{filiere_id}/enseignants",
            timeout=5.0,
        )
        resp.raise_for_status()
        enseignants = resp.json().get("enseignants", [])
        # Extraire les user_ids Keycloak non-null uniquement
        return [e["user_id"] for e in enseignants if e.get("user_id")]
    except Exception as exc:
        logger.error("get_teachers_of_filiere(%s) : %s", filiere_id, exc)
        return []


def get_filiere_name(filiere_id: int) -> str:
    """Retourne le nom d'une filière via ms-calendar /internal/filieres/{id}."""
    try:
        resp = httpx.get(
            f"{MS_CALENDAR_URL}/api/v1/calendar/internal/filieres/{filiere_id}",
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json().get("nom", f"Filière #{filiere_id}")
    except Exception as exc:
        logger.error("get_filiere_name(%s) : %s", filiere_id, exc)
        return f"Filière #{filiere_id}"


# Alias de compatibilité
get_teachers_of_filiere_for_notes = get_teachers_of_filiere


# Alias de compatibilité — scheduler.py et autres modules qui importent _headers
def _headers() -> dict:
    """Headers vides pour appels internes sans auth JWT."""
    return {}
