from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import notes
from services.mysql import init_db

app = FastAPI(
    title="ms-notes — ENT EST Salé",
    description=(
        "Micro-service de gestion des notes.\n\n"
        "**Types :** Notes d'examens, Contrôle continu, Moyennes générales.\n\n"
        "**Saisie :** Réservée aux enseignants et admins.\n\n"
        "**Consultation :** Étudiant voit uniquement ses propres notes."
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

app.include_router(notes.router)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ms-notes", "port": 8008}