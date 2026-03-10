from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FileUploadResponse(BaseModel):
    file_id: str
    title: str
    filename: str
    size_bytes: int
    category: str
    module: str
    minio_key: str
    upload_date: datetime
    message: str = "Fichier uploadé avec succès."

class DeleteResponse(BaseModel):
    file_id: str
    message: str
