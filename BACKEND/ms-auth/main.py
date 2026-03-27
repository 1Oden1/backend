from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, token

app = FastAPI(
    title="ms-auth — ENT EST Salé",
    description=(
        "Micro-service d'authentification.\n\n"
        "**Flux :** Login via Keycloak → émission de JWT maison (HS256).\n\n"
        "**Endpoint clé pour les autres services :** `POST /token/verify`"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(token.router)


@app.get("/health", tags=["Health"])
def health():
    """Vérification que le service est opérationnel."""
    return {"status": "ok", "service": "ms-auth", "port": 8001}