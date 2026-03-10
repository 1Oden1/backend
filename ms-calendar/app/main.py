import time
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.routers.calendar import router, internal_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MS-Calendar — ENT Salé",
    description=(
        "Microservice **source de vérité** pour la structure académique et l'emploi du temps.\n\n"
        "**Structure académique** : années, départements, filières, semestres, modules, éléments.\n\n"
        "**Emploi du temps** : enseignants, salles, séances.\n\n"
        "**Lecture** : tous les utilisateurs authentifiés.\n\n"
        "**Écriture / CRUD** : rôle `admin` uniquement.\n\n"
        "**Endpoints internes** : préfixe `/internal` — appels inter-services (ms-notes)."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _wait_for_db(retries: int = 15, delay: int = 3) -> bool:
    """
    Attend que MySQL soit opérationnel.
    Effectue jusqu'à `retries` tentatives espacées de `delay` secondes.
    """
    from app.database import engine

    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("MySQL est pret (tentative %d/%d).", attempt, retries)
            return True
        except Exception as exc:
            logger.warning(
                "MySQL pas encore pret (tentative %d/%d) : %s — nouvel essai dans %ds...",
                attempt, retries, exc, delay,
            )
            time.sleep(delay)

    logger.error("MySQL inaccessible apres %d tentatives. Migrations annulees.", retries)
    return False


def _run_migrations() -> None:
    """
    Applique les migrations Alembic via l'API Python (pas de subprocess).

    Avantages :
      - Pas de dependance au PATH ni au repertoire courant.
      - Les erreurs remontent comme de vraies exceptions Python.
      - Fonctionne meme si le binaire `alembic` n'est pas dans le PATH.
    """
    from alembic import command
    from alembic.config import Config

    # Resout le chemin vers alembic.ini depuis la racine du projet (/app)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))

    # Force le repertoire de script (robuste meme en cas de cwd inattendu)
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))

    logger.info("Application des migrations Alembic (upgrade head)...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations appliquees avec succes.")


@app.on_event("startup")
def startup_event():
    # Etape 1 : attendre MySQL
    if not _wait_for_db():
        raise RuntimeError(
            "MySQL inaccessible au demarrage — le service ne peut pas demarrer sans base de donnees."
        )

    # Etape 2 : appliquer les migrations via API Python Alembic
    try:
        _run_migrations()
    except Exception as exc:
        # Lever l'exception force Docker a redemarrer le conteneur (restart: unless-stopped)
        raise RuntimeError(f"Echec des migrations Alembic : {exc}") from exc


app.include_router(router,          prefix="/api/v1/calendar", tags=["Calendar"])
app.include_router(internal_router, prefix="/api/v1/calendar")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ms-calendar"}
