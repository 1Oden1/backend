import httpx
from fastapi import HTTPException
from config import settings


def get_admin_token() -> str:
    """Obtient un token admin Keycloak pour gérer les utilisateurs"""
    try:
        response = httpx.post(
            f"{settings.KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "client_id": "admin-cli",
                "username": "admin",
                "password": "admin",
                "grant_type": "password"
            },
            timeout=10.0
        )
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Keycloak indisponible")

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Erreur authentification Keycloak admin")

    return response.json()["access_token"]


def create_keycloak_user(username: str, email: str, first_name: str, last_name: str, password: str) -> str:
    """Crée un utilisateur dans Keycloak et retourne son ID"""
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    # Créer l'utilisateur
    response = httpx.post(
        f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users",
        json={
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": password, "temporary": False}]
        },
        headers=headers,
        timeout=10.0
    )

    if response.status_code == 409:
        raise HTTPException(status_code=409, detail="Utilisateur déjà existant")
    if response.status_code != 201:
        raise HTTPException(status_code=502, detail=f"Erreur création Keycloak: {response.text}")

    # Récupérer l'ID de l'utilisateur créé
    location = response.headers.get("Location", "")
    user_id = location.split("/")[-1]
    return user_id


def assign_keycloak_role(user_id: str, role_name: str):
    """Assigne un rôle client à un utilisateur Keycloak"""
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    # Récupérer l'ID du client
    response = httpx.get(
        f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/clients?clientId={settings.KEYCLOAK_CLIENT_ID}",
        headers=headers,
        timeout=10.0
    )
    clients = response.json()
    if not clients:
        raise HTTPException(status_code=404, detail="Client Keycloak non trouvé")
    client_id = clients[0]["id"]

    # Récupérer le rôle
    response = httpx.get(
        f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/clients/{client_id}/roles/{role_name}",
        headers=headers,
        timeout=10.0
    )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Rôle '{role_name}' non trouvé")
    role = response.json()

    # Assigner le rôle
    httpx.post(
        f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users/{user_id}/role-mappings/clients/{client_id}",
        json=[role],
        headers=headers,
        timeout=10.0
    )


def delete_keycloak_user(username: str):
    """Supprime un utilisateur de Keycloak"""
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Trouver l'utilisateur
    response = httpx.get(
        f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users?username={username}",
        headers=headers,
        timeout=10.0
    )
    users = response.json()
    if not users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé dans Keycloak")

    user_id = users[0]["id"]
    httpx.delete(
        f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users/{user_id}",
        headers=headers,
        timeout=10.0
    )