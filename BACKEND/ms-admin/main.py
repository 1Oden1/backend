from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import users, roles
from services.mysql import init_db

app = FastAPI(
    title="ms-admin — ENT EST Salé",
    description=(
        "Micro-service d'administration.\n\n"
        "**Fonctionnalités :** Gestion des utilisateurs et rôles via Keycloak + MySQL.\n\n"
        "**Sécurité :** Réservé aux utilisateurs avec le rôle `admin`."
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

app.include_router(users.router)
app.include_router(roles.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ms-admin", "port": 8006}