from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import courses, files

app = FastAPI(
    title="ms-download — ENT EST Salé",
    description=(
        "Micro-service de consultation et téléchargement de cours.\n\n"
        "**Fonctionnalités :** Liste des cours depuis MySQL, "
        "génération d'URLs signées MinIO pour téléchargement sécurisé.\n\n"
        "**Sécurité :** Accessible à tous les utilisateurs authentifiés (étudiant, enseignant, admin)."
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

app.include_router(courses.router)
app.include_router(files.router)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ms-download", "port": 8005}