import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

bearer_scheme = HTTPBearer()

REALM_URL = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"

async def get_public_key() -> str:
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{REALM_URL}/protocol/openid-connect/certs")
    certs = res.json()
    # Retourne la première clé publique RS256
    key = certs["keys"][0]
    return key

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
            audience="account",
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
