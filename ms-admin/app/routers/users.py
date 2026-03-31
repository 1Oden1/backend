from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List

from app.auth import require_admin, require_role
from app.keycloak_admin import (
    list_users, list_users_by_role, get_user, create_user,
    update_user, delete_user, reset_password,
    list_realm_roles,
)
from app.schemas import UserCreate, UserUpdate, UserRead, PasswordReset
from app.routers.audit import log_action

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

_require_authenticated = require_role("admin", "enseignant", "etudiant", "delegue")


@router.get(
    "/delegues",
    response_model=List[UserRead],
    summary="Lister les délégués (accessible aux enseignants)",
)
def list_delegues(_: dict = Depends(_require_authenticated)):
    try:
        return list_users_by_role("delegue")
    except Exception as e:
        raise HTTPException(502, f"Keycloak indisponible : {e}")


@router.get(
    "/enseignants-kc",
    response_model=List[UserRead],
    summary="Lister les enseignants Keycloak (accessible aux authentifiés)",
)
def list_enseignants_kc(_: dict = Depends(_require_authenticated)):
    try:
        return list_users_by_role("enseignant")
    except Exception as e:
        raise HTTPException(502, f"Keycloak indisponible : {e}")


@router.get(
    "/",
    response_model=List[UserRead],
    summary="Lister tous les utilisateurs Keycloak",
)
def list_all_users(
    search: str = Query("", description="Recherche par nom / email / username"),
    max: int    = Query(100, ge=1, le=500),
    admin: dict = Depends(require_admin),
):
    try:
        return list_users(search=search, max_results=max)
    except Exception as e:
        raise HTTPException(502, f"Keycloak indisponible : {e}")


@router.get(
    "/roles",
    summary="Lister les rôles disponibles dans le realm",
)
def get_realm_roles(_: dict = Depends(require_admin)):
    try:
        return list_realm_roles()
    except Exception as e:
        raise HTTPException(502, f"Keycloak indisponible : {e}")


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Détail d'un utilisateur",
)
def get_one_user(user_id: str, _: dict = Depends(require_admin)):
    try:
        return get_user(user_id)
    except Exception:
        raise HTTPException(404, "Utilisateur introuvable.")


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un utilisateur",
)
def create_new_user(body: UserCreate, admin: dict = Depends(require_admin)):
    try:
        user = create_user(
            username=body.username,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            password=body.password,
            roles=body.roles,
        )
    except Exception as e:
        raise HTTPException(400, f"Création impossible : {e}")

    log_action(
        admin_id=admin["sub"],
        action="CREATE_USER",
        target_type="user",
        target_id=user["id"],
        details=f"{body.username} | rôles : {body.roles}",
    )
    return user


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Modifier un utilisateur",
)
def update_existing_user(
    user_id: str,
    body: UserUpdate,
    admin: dict = Depends(require_admin),
):
    try:
        user = update_user(user_id, body.model_dump(exclude_none=True))
    except Exception as e:
        raise HTTPException(400, f"Modification impossible : {e}")

    log_action(
        admin_id=admin["sub"],
        action="UPDATE_USER",
        target_type="user",
        target_id=user_id,
        details=str(body.model_dump(exclude_none=True)),
    )
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un utilisateur",
)
def delete_existing_user(user_id: str, admin: dict = Depends(require_admin)):
    try:
        delete_user(user_id)
    except Exception as e:
        raise HTTPException(400, f"Suppression impossible : {e}")

    log_action(admin["sub"], "DELETE_USER", "user", user_id)


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Réinitialiser le mot de passe d'un utilisateur",
)
def reset_user_password(
    user_id: str,
    body: PasswordReset,
    admin: dict = Depends(require_admin),
):
    try:
        reset_password(user_id, body.new_password, body.temporary)
    except Exception as e:
        raise HTTPException(400, f"Réinitialisation impossible : {e}")

    log_action(admin["sub"], "RESET_PASSWORD", "user", user_id)
