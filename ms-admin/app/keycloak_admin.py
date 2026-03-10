"""
Client Keycloak Admin REST API.
"""
import httpx
from app.config import settings

_ADMIN_BASE = f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}"


def _get_admin_token() -> str:
    resp = httpx.post(
        f"{settings.KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type":  "password",
            "client_id":   "admin-cli",
            "username":    settings.KEYCLOAK_ADMIN_USER,
            "password":    settings.KEYCLOAK_ADMIN_PASSWORD,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_admin_token()}"}


def _normalize(u: dict) -> dict:
    """Convertit les clés camelCase de Keycloak en snake_case pour Pydantic."""
    return {
        "id":         u.get("id", ""),
        "username":   u.get("username", ""),
        "email":      u.get("email", ""),
        "first_name": u.get("firstName", ""),
        "last_name":  u.get("lastName", ""),
        "enabled":    u.get("enabled", True),
        "roles":      u.get("roles", []),
    }


# ── Utilisateurs ──────────────────────────────────────────────────────────────

def list_users(search: str = "", max_results: int = 100) -> list[dict]:
    resp = httpx.get(
        f"{_ADMIN_BASE}/users",
        headers=_headers(),
        params={"search": search, "max": max_results},
    )
    resp.raise_for_status()
    users = resp.json()
    for u in users:
        u["roles"] = get_user_roles(u["id"])
    return [_normalize(u) for u in users]


def get_user(user_id: str) -> dict:
    resp = httpx.get(f"{_ADMIN_BASE}/users/{user_id}", headers=_headers())
    resp.raise_for_status()
    u = resp.json()
    u["roles"] = get_user_roles(user_id)
    return _normalize(u)


def create_user(
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    roles: list[str],
    enabled: bool = True,
) -> dict:
    payload = {
        "username":  username,
        "email":     email,
        "firstName": first_name,
        "lastName":  last_name,
        "enabled":   enabled,
        "credentials": [
            {"type": "password", "value": password, "temporary": False}
        ],
    }
    resp = httpx.post(f"{_ADMIN_BASE}/users", json=payload, headers=_headers())
    resp.raise_for_status()

    location = resp.headers.get("Location", "")
    user_id = location.rstrip("/").split("/")[-1]

    if roles:
        assign_roles(user_id, roles)

    return get_user(user_id)


def update_user(user_id: str, data: dict) -> dict:
    payload = {}
    if "email"      in data: payload["email"]     = data["email"]
    if "first_name" in data: payload["firstName"] = data["first_name"]
    if "last_name"  in data: payload["lastName"]  = data["last_name"]
    if "enabled"    in data: payload["enabled"]   = data["enabled"]

    resp = httpx.put(f"{_ADMIN_BASE}/users/{user_id}", json=payload, headers=_headers())
    resp.raise_for_status()

    if "roles" in data:
        current = get_user_roles(user_id)
        if current:
            remove_roles(user_id, current)
        if data["roles"]:
            assign_roles(user_id, data["roles"])

    return get_user(user_id)


def delete_user(user_id: str) -> None:
    resp = httpx.delete(f"{_ADMIN_BASE}/users/{user_id}", headers=_headers())
    resp.raise_for_status()


def reset_password(user_id: str, new_password: str, temporary: bool = False) -> None:
    resp = httpx.put(
        f"{_ADMIN_BASE}/users/{user_id}/reset-password",
        json={"type": "password", "value": new_password, "temporary": temporary},
        headers=_headers(),
    )
    resp.raise_for_status()


# ── Rôles ─────────────────────────────────────────────────────────────────────

def list_realm_roles() -> list[dict]:
    resp = httpx.get(f"{_ADMIN_BASE}/roles", headers=_headers())
    resp.raise_for_status()
    return resp.json()


def get_user_roles(user_id: str) -> list[str]:
    resp = httpx.get(
        f"{_ADMIN_BASE}/users/{user_id}/role-mappings/realm",
        headers=_headers(),
    )
    resp.raise_for_status()
    return [r["name"] for r in resp.json()]


def _resolve_roles(role_names: list[str]) -> list[dict]:
    all_roles = {r["name"]: r for r in list_realm_roles()}
    return [{"id": all_roles[n]["id"], "name": n} for n in role_names if n in all_roles]


def assign_roles(user_id: str, role_names: list[str]) -> None:
    roles = _resolve_roles(role_names)
    if not roles:
        return
    resp = httpx.post(
        f"{_ADMIN_BASE}/users/{user_id}/role-mappings/realm",
        json=roles,
        headers=_headers(),
    )
    resp.raise_for_status()


def remove_roles(user_id: str, role_names: list[str]) -> None:
    roles = _resolve_roles(role_names)
    if not roles:
        return
    resp = httpx.request(
        "DELETE",
        f"{_ADMIN_BASE}/users/{user_id}/role-mappings/realm",
        json=roles,
        headers=_headers(),
    )
    resp.raise_for_status()
