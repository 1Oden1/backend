from fastapi import APIRouter, HTTPException, Depends
from app.schemas import LoginRequest, RefreshRequest, LogoutRequest, TokenResponse, UserInfo
from app.keycloak import keycloak_login, keycloak_refresh, keycloak_logout
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    try:
        data = await keycloak_login(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        token_type=data["token_type"],
        expires_in=data["expires_in"],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        data = await keycloak_refresh(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        token_type=data["token_type"],
        expires_in=data["expires_in"],
    )


@router.post("/logout")
async def logout(body: LogoutRequest):
    await keycloak_logout(body.refresh_token)
    return {"message": "Déconnexion réussie"}


@router.get("/me", response_model=UserInfo)
async def me(payload: dict = Depends(get_current_user)):
    roles = payload.get("realm_access", {}).get("roles", [])
    return UserInfo(
        id=payload.get("sub", ""),
        username=payload.get("preferred_username", ""),
        email=payload.get("email", ""),
        first_name=payload.get("given_name", ""),
        last_name=payload.get("family_name", ""),
        roles=roles,
    )

