from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.schemas import LoginRequest, LogoutRequest, TokenResponse, MessageResponse, TokenPayload
from services.keycloak import login_user, logout_user
from services.jwt import create_access_token, create_refresh_token, verify_token


router = APIRouter(prefix="/auth", tags=["Authentification"])

security = HTTPBearer()

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Connexion utilisateur",
    description="Authentifie via Keycloak et retourne access_token + refresh_token.",
)
def login(request: LoginRequest):
    """
    Flux :
    1. Keycloak valide username/password
    2. On extrait sub + rôles du token Keycloak
    3. On émet nos propres JWT (access + refresh) signés avec JWT_SECRET
    """
    kc_data = login_user(request.username, request.password)

    # Décoder le token Keycloak pour extraire les infos utilisateur
    # (jose peut décoder sans vérifier la signature Keycloak ici, on fait confiance au résultat)
    from jose import jwt as jose_jwt
    kc_payload = jose_jwt.get_unverified_claims(kc_data["access_token"])

    # Extraire le rôle depuis realm_access.roles (convention Keycloak)
    # APRÈS
    realm_roles = kc_payload.get("realm_access", {}).get("roles", [])
    client_roles = kc_payload.get("resource_access", {}).get("ent-client", {}).get("roles", [])
    all_roles = realm_roles + client_roles
    role = "admin" if "admin" in all_roles \
    else "enseignant" if "enseignant" in all_roles \
    else "teacher" if "teacher" in all_roles \
    else "etudiant" 

    token_data = {
        "sub": kc_payload.get("sub"),
        "username": kc_payload.get("preferred_username", request.username),
        "email": kc_payload.get("email", ""),
        "role": role,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 minutes en secondes
        role=role, 
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Déconnexion utilisateur",
    description="Révoque le refresh_token côté Keycloak.",
)
def logout(request: LogoutRequest):
    return logout_user(request.refresh_token)


@router.get(
    "/me",
    response_model=TokenPayload,
    summary="Profil utilisateur connecté",
    description="Retourne les infos de l'utilisateur à partir du JWT.",
)
def me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    return TokenPayload(
        sub=payload.get("sub"),
        username=payload.get("username"),
        email=payload.get("email"),
        role=payload.get("role"),
        exp=payload.get("exp"),
    )    