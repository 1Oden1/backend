"""
main.py — ms-notes
Migration Alembic désactivée au démarrage (tables déjà créées).
"""
import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.routers.admin      import router as admin_router
from app.routers.enseignant import router as enseignant_router
from app.routers.etudiant   import router as etudiant_router
from app.routers.internal   import router as internal_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _wait_for_db(retries: int = 20, delay: int = 3) -> bool:
    from app.database import engine
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("MySQL prêt.")
            return True
        except Exception as exc:
            logger.warning(
                "MySQL indisponible (tentative %d/%d) : %s", attempt, retries, exc
            )
            time.sleep(delay)
    return False


app = FastAPI(title="MS-Notes — ENT Salé", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(etudiant_router)
app.include_router(enseignant_router)
app.include_router(admin_router,    prefix="/api/v1/notes")
app.include_router(internal_router, prefix="/api/v1/notes")


@app.on_event("startup")
def startup_event():
    if not _wait_for_db():
        raise RuntimeError("MySQL inaccessible — arrêt.")
    logger.info("MS-Notes démarré. Migration Alembic ignorée (tables déjà à jour).")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "ms-notes", "version": "3.0.0"}
