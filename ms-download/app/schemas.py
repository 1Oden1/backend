from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FileMetadata(BaseModel):
    file_id: str
    owner_id: str
    owner_name: str
    title: str
    description: Optional[str] = None
    category: str
    module: str
    filename: str
    content_type: str
    size_bytes: int
    upload_date: datetime
    is_public: bool

class FileListResponse(BaseModel):
    total: int
    files: list[FileMetadata]

class DownloadLinkResponse(BaseModel):
    file_id: str
    filename: str
    download_url: str
    expires_in: str = "1 heure"
