from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import users, fichiers, audit
from app.routers.calendar_proxy import router as calendar_router
from app.routers.notes_proxy    import router as notes_router
from app.database_cassandra import init_cassandra

app = FastAPI(
    title="MS-Admin — ENT Salé",
    description=(
        "Microservice d'administration de l'ENT.\n\n"
        "**Architecture** : ms-admin est un **proxy pur**.\n"
        "- Il ne possède AUCUNE connexion directe vers `ent_calendar` ou `ent_notes`.\n"
        "- Toutes les opérations calendrier et notes sont déléguées via HTTP\n"
        "  aux endpoints des microservices dédiés (`ms-calendar`, `ms-notes`).\n\n"
        "**Accès direct** (ressources propres à ms-admin) :\n"
        "- Keycloak (gestion des utilisateurs/rôles)\n"
        "- MinIO + Cassandra (gestion des fichiers)\n"
        "- Cassandra `audit_logs` (journal d'audit)\n\n"
        "**Rôle requis :** `admin` sur tous les endpoints."
    ),
    version="2.0.0",
    servers=[{"url": "http://localhost:8006", "description": "Local"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    # Seule connexion DB propre à ms-admin : Cassandra pour audit_logs
    init_cassandra()


# ── Ressources propres à ms-admin ─────────────────────────────────────────────
app.include_router(users.router,    prefix="/api/v1/admin")
app.include_router(fichiers.router, prefix="/api/v1/admin")
app.include_router(audit.router,    prefix="/api/v1/admin")

# ── Proxies vers les microservices dédiés ────────────────────────────────────
app.include_router(calendar_router, prefix="/api/v1/admin")
app.include_router(notes_router,    prefix="/api/v1/admin")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ms-admin"}
