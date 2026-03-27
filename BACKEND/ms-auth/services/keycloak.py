import httpx
from fastapi import HTTPException
from config import settings


def _token_url() -> str:
    return (
        f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/token"
    )


def _logout_url() -> str:
    return (
        f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/logout"
    )


def login_user(username: str, password: str) -> dict:
    """
    Authentifie l'utilisateur via Keycloak (Resource Owner Password flow).
    Retourne access_token + refresh_token.
    """
    payload = {
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "openid profile email",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = httpx.post(_token_url(), data=payload, headers=headers, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Keycloak indisponible")

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Keycloak error: {response.text}")

    data = response.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "token_type": "bearer",
        "expires_in": data.get("expires_in", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    }


def logout_user(refresh_token: str) -> dict:
    """
    Révoque le refresh_token côté Keycloak (invalidation de session).
    """
    payload = {
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = httpx.post(_logout_url(), data=payload, headers=headers, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Keycloak indisponible")

    # 204 = succès sans contenu
    if response.status_code not in (200, 204):
        raise HTTPException(status_code=400, detail="Logout échoué ou token déjà révoqué")

    return {"message": "Déconnexion réussie"}