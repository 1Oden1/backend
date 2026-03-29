from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache
from app.config import settings

bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def get_keycloak_public_key() -> str:
    """Récupère et met en cache la clé publique Keycloak."""
    url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        key = resp.json()["public_key"]
        return f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Valide le JWT et retourne le payload utilisateur."""
    try:
        public_key = get_keycloak_public_key()
        payload = jwt.decode(
            credentials.credentials,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT invalide ou expiré.",
        )


def require_role(*roles: str):
    """Vérifie que l'utilisateur possède au moins l'un des rôles spécifiés."""
    def _check(user: dict = Depends(get_current_user)) -> dict:
        user_roles = user.get("realm_access", {}).get("roles", [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès réservé aux rôles : {list(roles)}",
            )
        return user
    return _check
