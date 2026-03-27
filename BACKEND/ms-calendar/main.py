from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import calendar
from services.mysql import init_db

app = FastAPI(
    title="ms-calendar — ENT EST Salé",
    description=(
        "Micro-service de gestion du calendrier.\n\n"
        "**Types d'événements :** Emploi du temps, Examens, Événements généraux.\n\n"
        "**Création :** Réservée aux admins et enseignants.\n\n"
        "**Consultation :** Accessible à tous les utilisateurs authentifiés."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

app.include_router(calendar.router)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ms-calendar", "port": 8007}