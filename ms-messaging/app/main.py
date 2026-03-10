import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import notifications, chat
from app.database_cassandra import init_cassandra
from app.rabbitmq import start_consumer
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Démarrage ─────────────────────────────────────────────────────────────

    # Initialisation Cassandra — ne bloque pas le démarrage si indisponible
    try:
        init_cassandra()
        logger.info("Cassandra initialisé.")
    except Exception as exc:
        logger.error(
            "Cassandra init failed (service will still start): %s", exc
        )

    # Lancer le consumer RabbitMQ en tâche de fond
    consumer_task = None
    try:
        consumer_task = asyncio.create_task(start_consumer())
        logger.info("Consumer RabbitMQ lancé en arrière-plan.")
    except Exception as exc:
        logger.error(
            "RabbitMQ consumer could not start (service will still start): %s", exc
        )

    # Lancer le scheduler APScheduler (rappels automatiques)
    scheduler = None
    try:
        scheduler = start_scheduler()
        logger.info("Scheduler démarré.")
    except Exception as exc:
        logger.error(
            "Scheduler could not start (service will still start): %s", exc
        )

    yield

    # ── Arrêt propre ──────────────────────────────────────────────────────────
    try:
        stop_scheduler()
    except Exception as exc:
        logger.error("Error stopping scheduler: %s", exc)

    if consumer_task is not None:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    logger.info("MS-Messaging arrêté proprement.")


app = FastAPI(
    title="MS-Messaging — ENT Salé",
    description=(
        "Microservice de messagerie et notifications de l'ENT.\n\n"
        "**Fonctionnalités :**\n"
        "- Notifications automatiques (événements filière, emploi du temps, notes).\n"
        "- Chat entre délégués ↔ enseignants, enseignants ↔ admin.\n"
        "- Diffusion (broadcast) admin → tous les enseignants.\n"
        "- Historique persisté en Cassandra, soft-delete côté UI.\n\n"
        "**Dépendances :** Keycloak · Cassandra (ent_messaging) · "
        "MySQL (ent_calendar + ent_notes) · RabbitMQ"
    ),
    version="1.0.0",
    servers=[{"url": "http://localhost:8007", "description": "Local"}],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notifications.router, prefix="/api/v1/messaging")
app.include_router(chat.router,          prefix="/api/v1/messaging")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "ms-messaging"}
