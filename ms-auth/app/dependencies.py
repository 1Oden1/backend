import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

bearer_scheme = HTTPBearer()

REALM_URL  = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
CERTS_URL  = f"{REALM_URL}/protocol/openid-connect/certs"

# ── Cache de la clé publique ───────────────────────────────────────────────────
# On ne va chercher la clé Keycloak qu'une seule fois au lieu de le faire
# à chaque requête (évite le httpx.ReadTimeout).
_public_key_cache: dict | None = None

async def get_public_key() -> dict:
    global _public_key_cache

    if _public_key_cache is not None:
        return _public_key_cache

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(CERTS_URL)
            res.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak inaccessible (timeout). Réessayez dans quelques instants.",
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erreur Keycloak : {str(e)}",
        )

    certs = res.json()
    # python-jose attend le JWKS complet {"keys": [...]}
    _public_key_cache = certs
    return _public_key_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials
    try:
        public_key = await get_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
