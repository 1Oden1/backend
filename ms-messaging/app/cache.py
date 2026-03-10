"""
cache.py — ms-messaging

Lecture/écriture du cache local Cassandra alimenté par les événements RabbitMQ.
Remplace tous les appels HTTP vers ms-notes et ms-calendar.

Tables utilisées :
  users_by_filiere   → (filiere_id, user_id, role)  — qui est dans quelle filière
  student_filiere    → (user_id, filiere_id)         — lookup inverse pour les étudiants
  filieres_cache     → (filiere_id, nom)             — noms des filières
"""
import logging
from app.database_cassandra import get_session
from app.config import settings

logger = logging.getLogger(__name__)


def _s():
    s = get_session()
    s.set_keyspace(settings.CASSANDRA_KEYSPACE)
    return s


# ── Étudiants ─────────────────────────────────────────────────────────────────

def cache_student_created(user_id: str, filiere_id: int) -> None:
    s = _s()
    s.execute(
        "INSERT INTO users_by_filiere (filiere_id, user_id, role) VALUES (%s, %s, 'student')",
        (filiere_id, user_id),
    )
    s.execute(
        "INSERT INTO student_filiere (user_id, filiere_id) VALUES (%s, %s)",
        (user_id, filiere_id),
    )
    logger.debug("Cache student created : %s → filière %s", user_id, filiere_id)


def cache_student_deleted(user_id: str, filiere_id: int) -> None:
    s = _s()
    s.execute(
        "DELETE FROM users_by_filiere WHERE filiere_id = %s AND user_id = %s",
        (filiere_id, user_id),
    )
    s.execute(
        "DELETE FROM student_filiere WHERE user_id = %s",
        (user_id,),
    )
    logger.debug("Cache student deleted : %s", user_id)


# ── Enseignants ───────────────────────────────────────────────────────────────

def cache_teacher_linked(user_id: str, filiere_id: int) -> None:
    """Ajoute l'enseignant à la filière (séance créée dans ms-calendar)."""
    s = _s()
    s.execute(
        "INSERT INTO users_by_filiere (filiere_id, user_id, role) VALUES (%s, %s, 'teacher')",
        (filiere_id, user_id),
    )
    logger.debug("Cache teacher linked : %s → filière %s", user_id, filiere_id)


def cache_teacher_deleted(user_id: str) -> None:
    """
    Supprime l'enseignant de toutes ses filières.
    On passe par student_filiere... mais les enseignants n'y sont pas.
    On scanne users_by_filiere avec ALLOW FILTERING (acceptable : suppression rare).
    """
    s = _s()
    rows = s.execute(
        "SELECT filiere_id FROM users_by_filiere WHERE user_id = %s ALLOW FILTERING",
        (user_id,),
    )
    for row in rows:
        s.execute(
            "DELETE FROM users_by_filiere WHERE filiere_id = %s AND user_id = %s",
            (row.filiere_id, user_id),
        )
    logger.debug("Cache teacher deleted : %s (toutes filières)", user_id)


# ── Filières ──────────────────────────────────────────────────────────────────

def cache_filiere_upsert(filiere_id: int, nom: str) -> None:
    s = _s()
    s.execute(
        "INSERT INTO filieres_cache (filiere_id, nom) VALUES (%s, %s)",
        (filiere_id, nom),
    )
    logger.debug("Cache filière upsert : %s → %s", filiere_id, nom)


def cache_filiere_deleted(filiere_id: int) -> None:
    s = _s()
    s.execute(
        "DELETE FROM filieres_cache WHERE filiere_id = %s",
        (filiere_id,),
    )
    logger.debug("Cache filière deleted : %s", filiere_id)


# ── Fonctions de lecture (remplacent http_clients.py) ─────────────────────────

def get_students_of_filiere(filiere_id: int) -> list[str]:
    """Retourne les user_ids des étudiants d'une filière depuis le cache."""
    s = _s()
    rows = s.execute(
        "SELECT user_id FROM users_by_filiere WHERE filiere_id = %s AND role = 'student' ALLOW FILTERING",
        (filiere_id,),
    )
    return [r.user_id for r in rows]


def get_teachers_of_filiere(filiere_id: int) -> list[str]:
    """Retourne les user_ids des enseignants d'une filière depuis le cache."""
    s = _s()
    rows = s.execute(
        "SELECT user_id FROM users_by_filiere WHERE filiere_id = %s AND role = 'teacher' ALLOW FILTERING",
        (filiere_id,),
    )
    return [r.user_id for r in rows]


def get_filiere_id_of_student(user_id: str) -> int | None:
    """Retourne la filière d'un étudiant depuis le cache."""
    s = _s()
    row = s.execute(
        "SELECT filiere_id FROM student_filiere WHERE user_id = %s",
        (user_id,),
    ).one_or_none()
    return row.filiere_id if row else None


def get_filiere_name(filiere_id: int) -> str:
    """Retourne le nom d'une filière depuis le cache."""
    s = _s()
    row = s.execute(
        "SELECT nom FROM filieres_cache WHERE filiere_id = %s",
        (filiere_id,),
    ).one_or_none()
    return row.nom if row else f"Filière #{filiere_id}"
