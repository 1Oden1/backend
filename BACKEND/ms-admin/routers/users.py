from fastapi import APIRouter, Header, HTTPException
from typing import List
from models.schemas import CreateUserRequest, UpdateUserRequest, UserResponse, SuccessResponse
from services.auth_client import require_admin
from services.keycloak import create_keycloak_user, assign_keycloak_role, delete_keycloak_user
from services.mysql import get_connection

router = APIRouter(prefix="/admin/users", tags=["Users"])


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.post("/", response_model=SuccessResponse, summary="Créer un utilisateur")
def create_user(request: CreateUserRequest, authorization: str = Header(None)):
    require_admin(get_token(authorization))

    # 1. Créer dans Keycloak
    user_id = create_keycloak_user(
        request.username, request.email,
        request.first_name, request.last_name,
        request.password
    )

    # 2. Assigner le rôle dans Keycloak
    assign_keycloak_role(user_id, request.role)

    # 3. Sauvegarder dans MySQL avec filiere
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, first_name, last_name, role, filiere) VALUES (%s, %s, %s, %s, %s, %s)",
        (request.username, request.email, request.first_name, request.last_name, request.role, request.filiere)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message=f"Utilisateur '{request.username}' créé avec succès")


@router.get("/", response_model=List[UserResponse], summary="Liste des utilisateurs")
def list_users(authorization: str = Header(None)):
    require_admin(get_token(authorization))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return users


@router.get("/{username}", response_model=UserResponse, summary="Détails d'un utilisateur")
def get_user(username: str, authorization: str = Header(None)):
    require_admin(get_token(authorization))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user


@router.put("/{username}", response_model=SuccessResponse, summary="Modifier un utilisateur")
def update_user(username: str, request: UpdateUserRequest, authorization: str = Header(None)):
    require_admin(get_token(authorization))

    conn = get_connection()
    cursor = conn.cursor()

    fields = []
    values = []
    if request.email:      fields.append("email = %s");      values.append(request.email)
    if request.first_name: fields.append("first_name = %s"); values.append(request.first_name)
    if request.last_name:  fields.append("last_name = %s");  values.append(request.last_name)
    if request.role:       fields.append("role = %s");       values.append(request.role)
    if request.filiere is not None:
        fields.append("filiere = %s")
        values.append(request.filiere)

    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")

    values.append(username)
    cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE username = %s", values)
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message=f"Utilisateur '{username}' mis à jour")


@router.delete("/{username}", response_model=SuccessResponse, summary="Supprimer un utilisateur")
def delete_user(username: str, authorization: str = Header(None)):
    require_admin(get_token(authorization))

    delete_keycloak_user(username)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message=f"Utilisateur '{username}' supprimé")