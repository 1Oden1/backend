import httpx
from app.config import settings

REALM_URL = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
TOKEN_URL  = f"{REALM_URL}/protocol/openid-connect/token"
LOGOUT_URL = f"{REALM_URL}/protocol/openid-connect/logout"
CERTS_URL  = f"{REALM_URL}/protocol/openid-connect/certs"

async def keycloak_login(username: str, password: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(TOKEN_URL, data={
            "grant_type":    "password",
            "client_id":     settings.KEYCLOAK_CLIENT_ID,
            "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
            "username":      username,
            "password":      password,
        })
    if res.status_code != 200:
        raise ValueError("Identifiants incorrects")
    return res.json()

async def keycloak_refresh(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(TOKEN_URL, data={
            "grant_type":    "refresh_token",
            "client_id":     settings.KEYCLOAK_CLIENT_ID,
            "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
            "refresh_token": refresh_token,
        })
    if res.status_code != 200:
        raise ValueError("Token invalide ou expiré")
    return res.json()

async def keycloak_logout(refresh_token: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(LOGOUT_URL, data={
            "client_id":     settings.KEYCLOAK_CLIENT_ID,
            "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
            "refresh_token": refresh_token,
        })
