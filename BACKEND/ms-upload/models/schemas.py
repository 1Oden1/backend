from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreateCoursRequest(BaseModel):
    titre: str
    description: Optional[str] = None
    matiere: str
    niveau: str  # L1, L2, L3, M1, M2


class CoursResponse(BaseModel):
    id: int
    titre: str
    description: Optional[str] = None
    matiere: str
    niveau: str
    enseignant: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileMetadataResponse(BaseModel):
    file_id: str
    cours_id: int
    filename: str
    original_name: str
    content_type: str
    size: int
    minio_path: str
    uploaded_by: str
    uploaded_at: datetime


class UploadResponse(BaseModel):
    message: str
    file_id: str
    cours_id: int
    filename: str
    size: int


class SuccessResponse(BaseModel):
    message: str