from fastapi import APIRouter, Header, HTTPException
from models.schemas import AssignRoleRequest, SuccessResponse
from services.auth_client import require_admin
from services.keycloak import assign_keycloak_role, get_admin_token
from services.mysql import get_connection
import httpx
from config import settings

router = APIRouter(prefix="/admin/roles", tags=["Roles"])


def get_token(authorization: str = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    return authorization.split(" ")[1]


@router.post(
    "/assign",
    response_model=SuccessResponse,
    summary="Assigner un rôle à un utilisateur",
    description="Change le rôle d'un utilisateur. Réservé aux admins."
)
def assign_role(request: AssignRoleRequest, authorization: str = Header(None)):
    require_admin(get_token(authorization))

    # Trouver l'ID Keycloak de l'utilisateur
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = httpx.get(
        f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users?username={request.username}",
        headers=headers,
        timeout=10.0
    )
    users = response.json()
    if not users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    user_id = users[0]["id"]
    assign_keycloak_role(user_id, request.role)

    # Mettre à jour MySQL
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET role = %s WHERE username = %s",
        (request.role, request.username)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message=f"Rôle '{request.role}' assigné à '{request.username}'")