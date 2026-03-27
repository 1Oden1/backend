import httpx
from fastapi import HTTPException
from config import settings


def verify_token(token: str) -> dict:
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


def require_enseignant_or_admin(token: str) -> dict:
    """Seuls enseignant et admin peuvent saisir/modifier les notes"""
    user = verify_token(token)
    if user.get("role") not in ("enseignant", "teacher", "admin"):
        raise HTTPException(status_code=403, detail="Accès réservé aux enseignants et admins")
    return user


def require_authenticated(token: str) -> dict:
    """Tout utilisateur authentifié"""
    return verify_token(token)