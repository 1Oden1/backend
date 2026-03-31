from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ── Notes ─────────────────────────────────────────────────────────────────────

class ElementNoteOut(BaseModel):
    calendar_element_id: int
    note: Optional[Decimal] = None

    class Config:
        from_attributes = True


class SemestreNotesOut(BaseModel):
    calendar_semestre_id: int
    moyenne_semestre:     Decimal
    notes:                List[ElementNoteOut]


# ── Étudiants ─────────────────────────────────────────────────────────────────

class EtudiantIn(BaseModel):
    user_id:             str
    cne:                 str
    prenom:              str
    nom:                 str
    calendar_filiere_id: int


class EtudiantRead(BaseModel):
    id:                  int
    user_id:             str
    cne:                 str
    prenom:              str
    nom:                 str
    calendar_filiere_id: int
    created_at:          datetime

    class Config:
        from_attributes = True


# ── Notes (saisie admin) ──────────────────────────────────────────────────────

class NoteIn(BaseModel):
    etudiant_id:         int
    calendar_element_id: int
    note:                Decimal


class NoteRead(BaseModel):
    id:                  int
    etudiant_id:         int
    calendar_element_id: int
    note:                Decimal
    created_at:          datetime
    updated_at:          datetime

    class Config:
        from_attributes = True


# ── Demandes de relevé ────────────────────────────────────────────────────────

class DemandeReleveIn(BaseModel):
    calendar_semestre_id: int


class DemandeReleve_EnseignantIn(BaseModel):
    etudiant_id:          int
    calendar_semestre_id: int


class DemandeReleveOut(BaseModel):
    id:                   int
    role_demandeur:       str
    etudiant_id:          int
    calendar_semestre_id: int
    statut:               str
    motif_rejet:          Optional[str]
    demande_le:           datetime
    traite_le:            Optional[datetime]

    class Config:
        from_attributes = True


class DemandeReleveRead(DemandeReleveOut):
    demandeur_user_id: str

    class Config:
        from_attributes = True


class ReleveOut(BaseModel):
    demande_id:   int
    etudiant_cne: str
    etudiant_nom: str
    notes:        SemestreNotesOut


# ── Demandes de classement ────────────────────────────────────────────────────

class DemandeClassementIn(BaseModel):
    calendar_semestre_id: int
    type_classement:      str   # "filiere" | "departement"


class DemandeClassementOut(BaseModel):
    id:                   int
    etudiant_id:          int
    calendar_semestre_id: int
    type_classement:      str
    statut:               str
    motif_rejet:          Optional[str]
    demande_le:           datetime
    traite_le:            Optional[datetime]

    class Config:
        from_attributes = True


class DemandeClassementRead(DemandeClassementOut):
    class Config:
        from_attributes = True


# ── Classements ───────────────────────────────────────────────────────────────

class EntreeClassement(BaseModel):
    rang:    int
    cne:     str
    nom:     str
    moyenne: Decimal


class ClassementCompletOut(BaseModel):
    scope_id:             int
    scope_nom:            str
    type_classement:      str
    calendar_semestre_id: int
    total:                int
    classement:           List[EntreeClassement]


class MonClassementOut(BaseModel):
    demande_id:           int
    type_classement:      str
    calendar_semestre_id: int
    scope_nom:            str
    total:                int
    mon_rang:             int
    ma_moyenne:           Decimal


# ── Traitement demandes (admin) ───────────────────────────────────────────────

class TraiterDemandeIn(BaseModel):
    statut:      str
    motif_rejet: Optional[str] = None


class AckResponse(BaseModel):
    detail: str
    count:  Optional[int] = None
