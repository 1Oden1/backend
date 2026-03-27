from fastapi import APIRouter
from models.schemas import TokenVerifyRequest, TokenRefreshRequest, TokenPayload
from services.jwt import verify_token, refresh_access_token

router = APIRouter(prefix="/token", tags=["Token"])


@router.post(
    "/verify",
    response_model=TokenPayload,
    summary="Vérifier un access token",
    description=(
        "Endpoint appelé par tous les autres micro-services pour valider un JWT. "
        "Retourne le payload (sub, role, email…) si valide, sinon HTTP 401."
    ),
    responses={
        200: {"description": "Token valide — payload retourné"},
        401: {"description": "Token invalide ou expiré"},
    },
)
def verify(request: TokenVerifyRequest):
    """
    Utilisé par : ms-ai, ms-upload, ms-download, ms-admin, ms-calendar, ms-notes, ms-messaging.
    Tous ces services font :  POST /token/verify  { "token": "<jwt>" }
    """
    payload = verify_token(request.token)
    return TokenPayload(
        sub=payload.get("sub"),
        username=payload.get("username"),
        email=payload.get("email"),
        role=payload.get("role"),
        exp=payload.get("exp"),
    )


@router.post(
    "/refresh",
    summary="Rafraîchir l'access token",
    description="Échange un refresh_token valide contre un nouvel access_token.",
    responses={
        200: {"description": "Nouvel access_token retourné"},
        401: {"description": "Refresh token invalide ou expiré"},
    },
)
def refresh(request: TokenRefreshRequest):
    return refresh_access_token(request.refresh_token)