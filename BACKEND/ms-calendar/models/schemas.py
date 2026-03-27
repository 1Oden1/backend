from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class TypeEvenement(str, Enum):
    cours = "cours"
    examen = "examen"
    evenement = "evenement"


class CreateEvenementRequest(BaseModel):
    titre: str
    description: Optional[str] = None
    type: TypeEvenement
    date_debut: datetime
    date_fin: datetime
    lieu: Optional[str] = None
    filiere: Optional[str] = None
    niveau: Optional[str] = None  # L1, L2, L3, M1, M2


class UpdateEvenementRequest(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    type: Optional[TypeEvenement] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    lieu: Optional[str] = None
    filiere: Optional[str] = None
    niveau: Optional[str] = None


class EvenementResponse(BaseModel):
    id: int
    titre: str
    description: Optional[str] = None
    type: str
    date_debut: datetime
    date_fin: datetime
    lieu: Optional[str] = None
    filiere: Optional[str] = None
    niveau: Optional[str] = None
    cree_par: str
    created_at: datetime

    class Config:
        from_attributes = True


class SuccessResponse(BaseModel):
    message: str