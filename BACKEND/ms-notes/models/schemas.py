from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TypeNote(str, Enum):
    examen = "examen"
    controle = "controle"
    moyenne = "moyenne"


class CreateNoteRequest(BaseModel):
    etudiant_username: str
    matiere: str
    type: TypeNote
    note: float = Field(..., ge=0, le=20)
    coefficient: float = Field(default=1.0, ge=0.5, le=5.0)
    semestre: Optional[str] = None  # S1, S2, S3...
    annee_universitaire: Optional[str] = None  # 2025-2026
    commentaire: Optional[str] = None


class UpdateNoteRequest(BaseModel):
    note: Optional[float] = Field(None, ge=0, le=20)
    coefficient: Optional[float] = Field(None, ge=0.5, le=5.0)
    commentaire: Optional[str] = None


class NoteResponse(BaseModel):
    id: int
    etudiant_username: str
    matiere: str
    type: str
    note: float
    coefficient: float
    semestre: Optional[str] = None
    annee_universitaire: Optional[str] = None
    commentaire: Optional[str] = None
    saisi_par: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MoyenneResponse(BaseModel):
    matiere: str
    moyenne: float
    nb_notes: int
    semestre: Optional[str] = None


class SuccessResponse(BaseModel):
    message: str