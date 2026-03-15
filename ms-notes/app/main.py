"""
main.py — ms-notes

Démarrage :
  1. Attente que MySQL soit prêt (retry loop)
  2. Migration Alembic via l'API Python (pas subprocess)
  3. Lancement FastAPI / Uvicorn
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


# ── Attente MySQL ─────────────────────────────────────────────────────────────

def _wait_for_db(retries: int = 20, delay: int = 3) -> bool:
    from app.database import engine
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("MySQL prêt.")
            return True
        except Exception as exc:
            logger.warning("MySQL indisponible (tentative %d/%d) : %s", attempt, retries, exc)
            time.sleep(delay)
    return False


# ── Migration Alembic ─────────────────────────────────────────────────────────

def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(base_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    command.upgrade(cfg, "head")
    logger.info("Migrations Alembic appliquées.")


# ── Application FastAPI ───────────────────────────────────────────────────────

app = FastAPI(
    title="MS-Notes — ENT Salé",
    description=(
        "Microservice propriétaire de la base `ent_notes`.\n\n"
        "**Étudiant** : consultation notes, demandes relevé/classement.\n\n"
        "**Enseignant** : classements filière/département, demandes relevé.\n\n"
        "**Admin** : CRUD complet via `/admin/`.\n\n"
        "**Interne** : `/internal/` appels inter-services."
    ),
    version="3.0.0",
)

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
        raise RuntimeError("MySQL inaccessible après plusieurs tentatives — arrêt du service.")

    # Migration : on tente, mais on ne bloque pas le démarrage si elle échoue
    # (les tables peuvent déjà exister dans le bon état)
    try:
        _run_migrations()
    except Exception as exc:
        logger.warning(
            "Migration Alembic non appliquée (tables probablement déjà à jour) : %s", exc
        )
        logger.info("Démarrage du service malgré l'avertissement de migration.")
        # On ne raise PAS → le service démarre quand même


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "ms-notes", "version": "3.0.0"}
