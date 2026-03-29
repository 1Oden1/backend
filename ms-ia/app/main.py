import json
import logging
from typing import AsyncIterator, List, Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
from jose import jwt, JWTError
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# ── Config ───────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3"
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "ent-sale"
    JWT_ALGORITHM: str = "RS256"
    MAX_HISTORY_MESSAGES: int = 20
    MAX_PROMPT_CHARS: int = 4000
    class Config:
        env_file = ".env"

settings = Settings()

# ── Auth ──────────────────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer()

@lru_cache(maxsize=1)
def get_keycloak_public_key() -> str:
    url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        key = resp.json()["public_key"]
        return f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return jwt.decode(
            credentials.credentials,
            get_keycloak_public_key(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT invalide ou expiré.")

# ── Schémas ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=settings.MAX_PROMPT_CHARS)
    history: Optional[List[Message]] = Field(default_factory=list)

class ChatResponse(BaseModel):
    reply: str
    model: str

# ── App ───────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ms-ia")

app = FastAPI(title="MS-IA — ENT Salé", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

SYSTEM_PROMPT = (
    "Tu es l'assistant IA de l'ENT de l'EST Salé, Maroc. "
    "Tu aides étudiants, enseignants et administrateurs sur la scolarité, "
    "les cours, les notes et la vie universitaire. "
    "Réponds toujours en français, sois concis et bienveillant."
)

def _build_messages(request: ChatRequest) -> list:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in (request.history or [])[-settings.MAX_HISTORY_MESSAGES:]:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})
    return messages

async def _stream_ollama(messages: list) -> AsyncIterator[str]:
    url = f"{settings.OLLAMA_URL}/api/chat"
    payload = {"model": settings.OLLAMA_MODEL, "messages": messages, "stream": True}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield f"data: {json.dumps({'error': 'Le modèle IA est indisponible.'})}\n\n"
                    return
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    done = chunk.get("done", False)
                    if token:
                        yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                    if done:
                        yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
                        return
    except httpx.ConnectError:
        yield f"data: {json.dumps({'error': 'Service IA en cours de démarrage, réessayez dans quelques instants.'})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "ms-ia"}

@app.post("/api/v1/ia/chat/stream")
async def chat_stream(request: ChatRequest, _user: dict = Depends(get_current_user)):
    return StreamingResponse(
        _stream_ollama(_build_messages(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/api/v1/ia/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, _user: dict = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            resp = await client.post(
                f"{settings.OLLAMA_URL}/api/chat",
                json={"model": settings.OLLAMA_MODEL, "messages": _build_messages(request), "stream": False}
            )
            if not resp.is_success:
                raise HTTPException(status_code=502, detail="Le modèle IA est indisponible.")
            return ChatResponse(reply=resp.json().get("message", {}).get("content", ""), model=settings.OLLAMA_MODEL)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service IA en cours de démarrage.")

@app.get("/api/v1/ia/models")
async def list_models(_user: dict = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            return resp.json() if resp.is_success else {"models": []}
    except Exception:
        return {"models": []}