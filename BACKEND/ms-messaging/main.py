from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import messages, notifications
from services.database import init_db

app = FastAPI(
    title="ms-messaging — ENT EST Salé",
    description=(
        "Micro-service de messagerie et notifications.\n\n"
        "**Fonctionnalités :** Messages entre utilisateurs, notifications in-app.\n\n"
        "**Sécurité :** Chaque endpoint vérifie le JWT via ms-auth."
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

app.include_router(messages.router)
app.include_router(notifications.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ms-messaging", "port": 8002}