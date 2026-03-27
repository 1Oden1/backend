from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


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
    uploaded_at: Optional[datetime] = None


class CoursWithFilesResponse(BaseModel):
    cours: CoursResponse
    files: List[FileMetadataResponse]


class DownloadUrlResponse(BaseModel):
    file_id: str
    original_name: str
    download_url: str
    expires_in: str