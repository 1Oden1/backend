from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import time, datetime, date
from decimal import Decimal
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────

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


# ════════════════════════════════════════════════════════════════════════════
# Utilisateurs (Keycloak)
# ════════════════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    username:   str       = Field(..., min_length=3, max_length=50)
    email:      EmailStr
    first_name: str       = Field(..., min_length=2, max_length=100)
    last_name:  str       = Field(..., min_length=2, max_length=100)
    password:   str       = Field(..., min_length=8)
    roles:      List[str] = Field(default_factory=list)

    model_config = {"json_schema_extra": {"example": {
        "username": "ali.benali", "email": "ali.benali@est-sale.ma",
        "first_name": "Ali", "last_name": "Benali",
        "password": "SecretPass123!", "roles": ["student"],
    }}}


class UserUpdate(BaseModel):
    email:      Optional[EmailStr]  = None
    first_name: Optional[str]       = None
    last_name:  Optional[str]       = None
    enabled:    Optional[bool]      = None
    roles:      Optional[List[str]] = None


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)
    temporary:    bool = False


class UserRead(BaseModel):
    id:         str
    username:   str
    email:      str
    first_name: str
    last_name:  str
    enabled:    bool
    roles:      List[str]


# ════════════════════════════════════════════════════════════════════════════
# Fichiers (Cassandra + MinIO)
# ════════════════════════════════════════════════════════════════════════════

class FileRead(BaseModel):
    file_id:      str
    owner_id:     str
    owner_name:   str
    title:        str
    description:  Optional[str]
    category:     Optional[str]
    module:       Optional[str]
    filename:     str
    content_type: str
    size_bytes:   int
    upload_date:  datetime
    is_public:    bool
    minio_key:    str


class FileListResponse(BaseModel):
    total: int
    files: List[FileRead]


class FileVisibilityUpdate(BaseModel):
    is_public: bool


# ════════════════════════════════════════════════════════════════════════════
# Calendar — ent_calendar
# ════════════════════════════════════════════════════════════════════════════

class DepartementIn(BaseModel):
    nom: str = Field(..., min_length=2, max_length=150)

class DepartementRead(BaseModel):
    id:  int
    nom: str
    model_config = {"from_attributes": True}


class FiliereIn(BaseModel):
    nom:            str = Field(..., min_length=2, max_length=150)
    departement_id: int

class FiliereRead(BaseModel):
    id:             int
    nom:            str
    departement_id: int
    model_config = {"from_attributes": True}


class SemestreCalendarIn(BaseModel):
    nom:        str = Field(..., max_length=20)
    filiere_id: int

class SemestreCalendarRead(BaseModel):
    id:         int
    nom:        str
    filiere_id: int
    model_config = {"from_attributes": True}


class ModuleCalendarIn(BaseModel):
    nom:         str = Field(..., max_length=150)
    credit:      int = Field(..., ge=1, le=10)
    semestre_id: int

class ModuleCalendarRead(BaseModel):
    id:          int
    nom:         str
    credit:      int
    semestre_id: int
    model_config = {"from_attributes": True}


class ElementModuleCalendarIn(BaseModel):
    nom:       str           = Field(..., max_length=150)
    type:      TypeElementEnum
    module_id: int

class ElementModuleCalendarRead(BaseModel):
    id:        int
    nom:       str
    type:      TypeElementEnum
    module_id: int
    model_config = {"from_attributes": True}


class EnseignantCalendarIn(BaseModel):
    nom:     str      = Field(..., max_length=100)
    prenom:  str      = Field(..., max_length=100)
    email:   EmailStr
    user_id: Optional[str] = None

class EnseignantCalendarRead(BaseModel):
    id:      int
    nom:     str
    prenom:  str
    email:   str
    user_id: Optional[str]
    model_config = {"from_attributes": True}


class SalleIn(BaseModel):
    nom:      str                    = Field(..., max_length=50)
    capacite: Optional[int]          = None
    type:     Optional[TypeSalleEnum] = None

class SalleRead(BaseModel):
    id:       int
    nom:      str
    capacite: Optional[int]
    type:     Optional[TypeSalleEnum]
    model_config = {"from_attributes": True}


class SeanceIn(BaseModel):
    jour:              JourEnum
    heure_debut:       time
    heure_fin:         time
    element_module_id: int
    enseignant_id:     int
    salle_id:          int

class SeanceUpdate(BaseModel):
    jour:          Optional[JourEnum] = None
    heure_debut:   Optional[time]     = None
    heure_fin:     Optional[time]     = None
    enseignant_id: Optional[int]      = None
    salle_id:      Optional[int]      = None

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


class EmploiDuTemps(BaseModel):
    departement: str
    filiere:     str
    semestre:    str
    seances:     List[SeanceRead]


# ════════════════════════════════════════════════════════════════════════════
# Notes — ent_notes
# ════════════════════════════════════════════════════════════════════════════

class AnneeUniversitaireIn(BaseModel):
    label: str = Field(..., max_length=20, description="Ex : 2024-2025")

class AnneeUniversitaireRead(BaseModel):
    id:    int
    label: str
    model_config = {"from_attributes": True}


class DepartementNotesIn(BaseModel):
    nom: str = Field(..., min_length=2, max_length=150)

class DepartementNotesRead(BaseModel):
    id:  int
    nom: str
    model_config = {"from_attributes": True}


class FiliereNotesIn(BaseModel):
    nom:            str = Field(..., min_length=2, max_length=150)
    departement_id: int

class FiliereNotesRead(BaseModel):
    id:             int
    nom:            str
    departement_id: int
    model_config = {"from_attributes": True}


class SemestreNotesIn(BaseModel):
    nom:               str            = Field(..., max_length=10)
    annee_id:          int
    filiere_id:        int
    date_limite_depot: Optional[date] = Field(
        None, description="Date limite de dépôt des notes (YYYY-MM-DD). "
                          "Un rappel automatique est envoyé aux enseignants 7 jours avant."
    )

class SemestreNotesRead(BaseModel):
    id:                int
    nom:               str
    annee_id:          int
    filiere_id:        int
    date_limite_depot: Optional[date] = None
    model_config = {"from_attributes": True}

class DeadlineUpdate(BaseModel):
    date_limite_depot: Optional[date] = Field(
        None,
        description="Nouvelle date limite de dépôt des notes (YYYY-MM-DD). "
                    "Mettre null pour supprimer la deadline."
    )
    model_config = {"json_schema_extra": {"example": {"date_limite_depot": "2025-06-15"}}}


class ModuleNotesIn(BaseModel):
    nom:         str = Field(..., max_length=150)
    code:        str = Field(..., max_length=30)
    credit:      int = Field(..., ge=1, le=10)
    semestre_id: int

class ModuleNotesRead(BaseModel):
    id:          int
    nom:         str
    code:        str
    credit:      int
    semestre_id: int
    model_config = {"from_attributes": True}


class ElementModuleNotesIn(BaseModel):
    nom:         str           = Field(..., max_length=150)
    code:        str           = Field(..., max_length=30)
    coefficient: float         = Field(..., gt=0, le=1)
    module_id:   int

class ElementModuleNotesRead(BaseModel):
    id:          int
    nom:         str
    code:        str
    coefficient: Decimal
    module_id:   int
    model_config = {"from_attributes": True}


class EtudiantIn(BaseModel):
    user_id:    str       = Field(..., description="UUID Keycloak")
    cne:        str       = Field(..., max_length=20)
    prenom:     str       = Field(..., max_length=100)
    nom:        str       = Field(..., max_length=100)
    filiere_id: int

class EtudiantRead(BaseModel):
    id:         int
    user_id:    str
    cne:        str
    prenom:     str
    nom:        str
    filiere_id: int
    model_config = {"from_attributes": True}


class EnseignantNotesIn(BaseModel):
    user_id:        str = Field(..., description="UUID Keycloak")
    prenom:         str = Field(..., max_length=100)
    nom:            str = Field(..., max_length=100)
    departement_id: int

class EnseignantNotesRead(BaseModel):
    id:             int
    user_id:        str
    prenom:         str
    nom:            str
    departement_id: int
    model_config = {"from_attributes": True}


class NoteIn(BaseModel):
    etudiant_id: int
    element_id:  int
    note:        float = Field(..., ge=0, le=20)

    model_config = {"json_schema_extra": {"example": {
        "etudiant_id": 1, "element_id": 2, "note": 14.5,
    }}}

class NoteRead(BaseModel):
    id:          int
    etudiant_id: int
    element_id:  int
    note:        Decimal
    model_config = {"from_attributes": True}


class DemandeReleveRead(BaseModel):
    id:                int
    demandeur_user_id: str
    role_demandeur:    str
    etudiant_id:       int
    semestre_id:       int
    statut:            str
    motif_rejet:       Optional[str]
    demande_le:        datetime
    traite_le:         Optional[datetime]
    model_config = {"from_attributes": True}


class DemandeClassementRead(BaseModel):
    id:              int
    etudiant_id:     int
    semestre_id:     int
    type_classement: str
    statut:          str
    motif_rejet:     Optional[str]
    demande_le:      datetime
    traite_le:       Optional[datetime]
    model_config = {"from_attributes": True}


class TraiterDemandeIn(BaseModel):
    statut:      str           = Field(..., pattern="^(approuve|rejete)$")
    motif_rejet: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# Audit
# ════════════════════════════════════════════════════════════════════════════

class AuditLogRead(BaseModel):
    log_id:      str
    admin_id:    str
    action:      str
    target_type: str
    target_id:   str
    details:     str
    created_at:  datetime


class AckResponse(BaseModel):
    detail: str
    count:  Optional[int] = None
