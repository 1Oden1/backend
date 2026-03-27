from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException
from config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(data: dict) -> str:
    """
    Crée un access token JWT signé (expire dans ACCESS_TOKEN_EXPIRE_MINUTES).
    `data` doit contenir au minimum {"sub": user_id, "role": "..."}.
    """
    payload = data.copy()
    payload["exp"] = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["iat"] = _now()
    payload["type"] = "access"
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Crée un refresh token JWT signé (expire dans REFRESH_TOKEN_EXPIRE_DAYS).
    Contient uniquement sub + type pour minimiser l'exposition.
    """
    payload = {
        "sub": data["sub"],
        "exp": _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": _now(),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """
    Décode et valide un access token JWT.
    - Lève HTTP 401 si expiré ou invalide.
    - Retourne le payload complet (sub, role, email, exp…).
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        # S'assurer que c'est bien un access token
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token de type incorrect")
        return payload

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")


def refresh_access_token(refresh_token_str: str) -> dict:
    """
    Valide un refresh token et émet un nouveau access token.
    Retourne {"access_token": ..., "token_type": "bearer", "expires_in": ...}.
    """
    try:
        payload = jwt.decode(
            refresh_token_str,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expiré, reconnectez-vous")
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de type incorrect")

    new_access = create_access_token({
        "sub": payload["sub"],
        "role": payload.get("role", ""),
        "email": payload.get("email", ""),
        "username": payload.get("username", ""),
    })
    return {
        "access_token": new_access,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }