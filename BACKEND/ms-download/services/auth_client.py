import httpx
from fastapi import HTTPException
from config import settings


def verify_token(token: str) -> dict:
    """Vérifie le JWT via ms-auth — accessible à tous les rôles"""
    try:
        response = httpx.post(
            f"{settings.MS_AUTH_URL}/token/verify",
            json={"token": token},
            timeout=5.0
        )
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="ms-auth indisponible")

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Erreur ms-auth")

    return response.json()


def require_authenticated(token: str) -> dict:
    """Vérifie que l'utilisateur est authentifié (tout rôle accepté)"""
    return verify_token(token)