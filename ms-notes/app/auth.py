import logging
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def get_keycloak_public_key() -> str:
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
        get_keycloak_public_key.cache_clear()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Keycloak inaccessible (timeout).")
    except httpx.HTTPStatusError as exc:
        get_keycloak_public_key.cache_clear()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            f"Keycloak a retourné une erreur {exc.response.status_code}.")
    except Exception as exc:
        get_keycloak_public_key.cache_clear()
        logger.error("Erreur récupération clé Keycloak : %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Impossible de contacter Keycloak.")


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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Token JWT invalide ou expiré : {exc}")
    except Exception as exc:
        logger.error("Erreur vérification JWT : %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Erreur d'authentification.")


def require_role(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        user_roles = user.get("realm_access", {}).get("roles", [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Accès réservé aux rôles : {list(roles)}.",
            )
        return user
    return checker


require_etudiant   = require_role("etudiant")
require_enseignant = require_role("enseignant")
require_admin      = require_role("admin")

# Un délégué est un étudiant avec des droits supplémentaires
# → il doit pouvoir accéder à toutes les routes étudiants
require_student = require_role("etudiant", "delegue")
require_teacher = require_enseignant
