from pydantic import BaseModel
from typing import Optional, List
from datetime import time, date
from decimal import Decimal
from enum import Enum


class TypeElementEnum(str, Enum):
    cours = "Cours"
    td    = "TD"
    tp    = "TP"

class JourEnum(str, Enum):
    lundi    = "Lundi"
    mardi    = "Mardi"
    mercredi = "Mercredi"
    jeudi    = "Jeudi"
    vendredi = "Vendredi"
    samedi   = "Samedi"

class TypeSalleEnum(str, Enum):
    amphi      = "Amphithéâtre"
    salle_td   = "Salle TD"
    salle_tp   = "Salle TP"
    salle_info = "Salle Info"


# ── Années universitaires ─────────────────────────────────────────────────────

class AnneeUniversitaireIn(BaseModel):
    label: str

class AnneeUniversitaireRead(BaseModel):
    id:    int
    label: str
    model_config = {"from_attributes": True}


# ── Départements ──────────────────────────────────────────────────────────────

class DepartementIn(BaseModel):
    nom: str

class DepartementRead(BaseModel):
    id:  int
    nom: str
    model_config = {"from_attributes": True}


# ── Filières ──────────────────────────────────────────────────────────────────

class FiliereIn(BaseModel):
    nom:            str
    departement_id: int

class FiliereRead(BaseModel):
    id:             int
    nom:            str
    departement_id: int
    model_config = {"from_attributes": True}


# ── Semestres ─────────────────────────────────────────────────────────────────

class SemestreIn(BaseModel):
    nom:               str
    annee_id:          int
    filiere_id:        int
    date_limite_depot: Optional[date] = None

class DeadlineUpdate(BaseModel):
    date_limite_depot: Optional[date] = None

class SemestreRead(BaseModel):
    id:                int
    nom:               str
    annee_id:          int
    filiere_id:        int
    date_limite_depot: Optional[date] = None
    model_config = {"from_attributes": True}


# ── Modules ───────────────────────────────────────────────────────────────────

class ModuleIn(BaseModel):
    nom:         str
    code:        str
    credit:      int = 2
    semestre_id: int

class ModuleRead(BaseModel):
    id:          int
    nom:         str
    code:        str
    credit:      int
    semestre_id: int
    model_config = {"from_attributes": True}


# ── Éléments de module ────────────────────────────────────────────────────────

class ElementModuleIn(BaseModel):
    nom:         str
    code:        str
    # BUG FIX #3 : coefficient était absent
    coefficient: Decimal = Decimal("1")
    type:        TypeElementEnum = TypeElementEnum.cours
    module_id:   int

class ElementModuleRead(BaseModel):
    id:          int
    nom:         str
    code:        str
    # BUG FIX #3 : coefficient était absent
    coefficient: Decimal
    type:        TypeElementEnum
    module_id:   int
    model_config = {"from_attributes": True}


# ── Enseignants ───────────────────────────────────────────────────────────────

class EnseignantIn(BaseModel):
    user_id: Optional[str] = None
    nom:     str
    prenom:  str
    email:   str

class EnseignantRead(BaseModel):
    id:      int
    user_id: Optional[str] = None
    nom:     str
    prenom:  str
    email:   str
    model_config = {"from_attributes": True}


# ── Salles ────────────────────────────────────────────────────────────────────

class SalleIn(BaseModel):
    nom:      str
    capacite: Optional[int]           = None
    type:     Optional[TypeSalleEnum] = None

class SalleRead(BaseModel):
    id:       int
    nom:      str
    capacite: Optional[int]
    type:     Optional[TypeSalleEnum]
    model_config = {"from_attributes": True}


# ── Séances ───────────────────────────────────────────────────────────────────

class SeanceIn(BaseModel):
    jour:              JourEnum
    heure_debut:       time
    heure_fin:         time
    element_module_id: int
    enseignant_id:     int
    salle_id:          int

class SeanceRead(BaseModel):
    id:                int
    jour:              JourEnum
    heure_debut:       time
    heure_fin:         time
    element_module:    str
    type_seance:       TypeElementEnum
    module:            str
    enseignant_nom:    str
    enseignant_prenom: str
    salle:             str


# ── Emploi du temps ───────────────────────────────────────────────────────────

class EmploiDuTemps(BaseModel):
    departement: str
    filiere:     str
    annee:       str
    semestre:    str
    seances:     List[SeanceRead]
