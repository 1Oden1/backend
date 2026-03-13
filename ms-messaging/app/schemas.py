from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class NotificationType(str, Enum):
    filiere_event     = "filiere_event"      # événement filière → étudiants + enseignants
    schedule_update   = "schedule_update"    # MAJ emploi du temps → enseignant concerné
    grade_reminder    = "grade_reminder"     # rappel dépôt notes → enseignants
    grades_available  = "grades_available"   # notes/classement publiés → étudiants + enseignants
    new_message       = "new_message"        # nouveau message de chat


class ConversationType(str, Enum):
    direct    = "direct"     # discussion 1-à-1
    broadcast = "broadcast"  # message de diffusion admin → tous les enseignants


# ════════════════════════════════════════════════════════════════════════════
# Notifications
# ════════════════════════════════════════════════════════════════════════════

class NotificationRead(BaseModel):
    notification_id: str
    type:            NotificationType
    title:           str
    content:         str
    related_id:      Optional[str] = None
    is_read:         bool
    created_at:      datetime


class NotificationListResponse(BaseModel):
    total:         int
    notifications: List[NotificationRead]


# ── Payloads entrants (appelés par d'autres microservices ou l'admin) ─────────

class FiliereEventIn(BaseModel):
    """Événement concernant toute une filière (admin)."""
    filiere_id: int
    title:      str = Field(..., min_length=3, max_length=200)
    content:    str = Field(..., min_length=3, max_length=1000)

    model_config = {"json_schema_extra": {"example": {
        "filiere_id": 1,
        "title":   "Réunion pédagogique",
        "content": "Une réunion est prévue le 10/06 à 10h en salle A1.",
    }}}


class ScheduleUpdateIn(BaseModel):
    """Mise à jour de l'emploi du temps d'un enseignant (ms-calendar)."""
    enseignant_user_id: str = Field(..., description="user_id Keycloak de l'enseignant")
    title:              str = Field(..., min_length=3, max_length=200)
    content:            str = Field(..., min_length=3, max_length=1000)
    seance_id:          Optional[int] = None

    model_config = {"json_schema_extra": {"example": {
        "enseignant_user_id": "abc-123",
        "title":   "Changement de salle",
        "content": "Votre séance de Maths du Lundi 08h est déplacée en Salle Info 2.",
        "seance_id": 42,
    }}}


class GradeReminderIn(BaseModel):
    """Rappel dépôt des notes — envoyé aux enseignants de la filière (admin / scheduler)."""
    filiere_id:         int
    semestre_id:        int
    date_limite:        str  = Field(..., description="Ex : 2025-06-15")
    jours_restants:     int  = Field(..., ge=1)

    model_config = {"json_schema_extra": {"example": {
        "filiere_id": 1, "semestre_id": 2,
        "date_limite": "2025-06-15", "jours_restants": 7,
    }}}


class GradesAvailableIn(BaseModel):
    """Notes et classement publiés — notifie étudiants + enseignants de la filière (ms-notes)."""
    filiere_id:  int
    semestre_id: int

    model_config = {"json_schema_extra": {"example": {
        "filiere_id": 1, "semestre_id": 2,
    }}}


# ════════════════════════════════════════════════════════════════════════════
# Chat — Messages & Conversations
# ════════════════════════════════════════════════════════════════════════════

class MessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageRead(BaseModel):
    message_id:      str
    conversation_id: str
    sender_id:       str
    sender_name:     str
    content:         str
    sent_at:         datetime
    is_hidden:       bool  # True si masqué pour l'utilisateur courant


class MessageListResponse(BaseModel):
    conversation_id: str
    messages:        List[MessageRead]


class ConversationStartIn(BaseModel):
    """Démarrer ou récupérer une conversation directe avec un autre utilisateur."""
    target_user_id:    str       = Field(..., description="user_id Keycloak du destinataire")
    target_user_name:  str       = Field(..., description="Nom affiché du destinataire")
    target_user_roles: List[str] = Field(default=[], description="Rôles pré-récupérés par le frontend")


class ConversationRead(BaseModel):
    conversation_id: str
    type:            ConversationType
    other_user_id:   str
    other_user_name: str
    last_message_at: Optional[datetime] = None


class BroadcastIn(BaseModel):
    """Diffusion admin → tous les enseignants."""
    content: str = Field(..., min_length=1, max_length=2000)

    model_config = {"json_schema_extra": {"example": {
        "content": "Chers enseignants, la réunion de département est reportée au 12/06.",
    }}}


# ════════════════════════════════════════════════════════════════════════════
# Réponses génériques
# ════════════════════════════════════════════════════════════════════════════

class AckResponse(BaseModel):
    detail: str
    count:  Optional[int] = None
