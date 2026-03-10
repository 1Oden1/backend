"""
Router internal — /api/v1/notes/internal
Appels inter-services uniquement (non exposé dans Swagger public).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/internal", tags=["Internal"], include_in_schema=False)


@router.get("/health")
def internal_health(_=Depends(get_current_user)):
    return {"status": "ok", "service": "ms-notes"}
