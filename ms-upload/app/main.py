from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import upload
from app.database import init_cassandra

app = FastAPI(
    title="MS-Upload — ENT Salé",
    description="Microservice d'ajout de fichiers pédagogiques.",
    version="1.0.0",
    servers=[{"url": "http://localhost:8002", "description": "Local"}]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_cassandra()

app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ms-upload"}
