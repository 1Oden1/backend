from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import courses, files
from services.mysql import init_db
from services.cassandra import init_cassandra

app = FastAPI(
    title="ms-upload — ENT EST Salé",
    description=(
        "Micro-service d'upload de cours.\n\n"
        "**Fonctionnalités :** Upload fichiers (PDF, DOCX) → MinIO + métadonnées Cassandra + MySQL.\n\n"
        "**Sécurité :** Réservé aux utilisateurs avec le rôle `enseignant` ou `admin`."
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
    init_cassandra()

app.include_router(courses.router)
app.include_router(files.router)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ms-upload", "port": 8004}