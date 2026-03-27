from pydantic import BaseModel
from typing import Optional


# ── Requêtes ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenVerifyRequest(BaseModel):
    token: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# ── Réponses ─────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int                  # secondes avant expiration access_token
    role: Optional[str] = None 
    

class TokenPayload(BaseModel):
    """Payload retourné par /token/verify — utilisé par tous les autres ms."""
    sub: str                         # user_id (depuis Keycloak)
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None       # "student" | "teacher" | "admin"
    exp: Optional[int] = None


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str