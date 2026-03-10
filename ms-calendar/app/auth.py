import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache
from app.config import settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def get_keycloak_public_key() -> str:
    """
    Récupère la clé publique RSA depuis Keycloak.
    BUG FIX : exceptions httpx non catchées → 500 quand Keycloak est indisponible.
    """
    url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if "public_key" not in data:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Clé publique absente de la réponse Keycloak.",
                )
            return (
                f"-----BEGIN PUBLIC KEY-----\n"
                f"{data['public_key']}\n"
                f"-----END PUBLIC KEY-----"
            )
    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.error("Timeout connexion Keycloak : %s", url)
        get_keycloak_public_key.cache_clear()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak inaccessible (timeout).",
        )
    except httpx.HTTPStatusError as exc:
        logger.error("Keycloak HTTP %s : %s", exc.response.status_code, url)
        get_keycloak_public_key.cache_clear()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Keycloak a retourné une erreur {exc.response.status_code}.",
        )
    except Exception as exc:
        logger.error("Erreur récupération clé Keycloak : %s", exc)
        get_keycloak_public_key.cache_clear()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Impossible de contacter Keycloak.",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    try:
        public_key = get_keycloak_public_key()
        return jwt.decode(
            credentials.credentials,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except HTTPException:
        raise
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token JWT invalide ou expiré : {exc}",
        )
    except Exception as exc:
        logger.error("Erreur vérification JWT : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur d'authentification.",
        )


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    # BUG FIX : "ent-backend" hardcodé → utilise settings.KEYCLOAK_CLIENT_ID
    roles = (
        user.get("realm_access", {}).get("roles", [])
        + user.get("resource_access", {})
              .get(settings.KEYCLOAK_CLIENT_ID, {})
              .get("roles", [])
    )
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return user
