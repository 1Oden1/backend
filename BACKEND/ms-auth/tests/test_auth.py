import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

client = TestClient(app)

# ── Données de test ───────────────────────────────────────────────────────────

FAKE_KC_ACCESS = (
    # JWT Keycloak factice (non signé, pour les tests uniquement)
    "eyJhbGciOiJSUzI1NiJ9."
    "eyJzdWIiOiJ1c2VyLTEyMyIsInByZWZlcnJlZF91c2VybmFtZSI6ImV0dWRpYW50MSIsImVtYWlsIjoiZXR1ZGlhbnQxQGVzdC1zYWxlLm1hIiwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbInN0dWRlbnQiXX19."
    "signature"
)

FAKE_KC_RESPONSE = {
    "access_token": FAKE_KC_ACCESS,
    "refresh_token": "fake_refresh",
    "expires_in": 1800,
}

# ── Tests /health ─────────────────────────────────────────────────────────────

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "ms-auth"
    assert resp.json()["status"] == "ok"


# ── Tests /auth/login ─────────────────────────────────────────────────────────

@patch("routers.auth.login_user", return_value=FAKE_KC_RESPONSE)
def test_login_success(mock_login):
    resp = client.post("/auth/login", json={"username": "etudiant1", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800


@patch("routers.auth.login_user", side_effect=Exception("Identifiants incorrects"))
def test_login_wrong_credentials(mock_login):
    resp = client.post("/auth/login", json={"username": "bad", "password": "wrong"})
    assert resp.status_code != 200


def test_login_missing_fields():
    resp = client.post("/auth/login", json={"username": "only_user"})
    assert resp.status_code == 422  # Validation Pydantic


# ── Tests /auth/logout ────────────────────────────────────────────────────────

@patch("routers.auth.logout_user", return_value={"message": "Déconnexion réussie"})
def test_logout_success(mock_logout):
    resp = client.post("/auth/logout", json={"refresh_token": "some_refresh_token"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Déconnexion réussie"


def test_logout_missing_token():
    resp = client.post("/auth/logout", json={})
    assert resp.status_code == 422


# ── Tests /token/verify ───────────────────────────────────────────────────────

def test_verify_valid_token():
    """Crée un vrai token puis le vérifie."""
    from services.jwt import create_access_token
    token = create_access_token({
        "sub": "user-123",
        "username": "etudiant1",
        "email": "etudiant1@est-sale.ma",
        "role": "student",
    })
    resp = client.post("/token/verify", json={"token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sub"] == "user-123"
    assert data["role"] == "student"
    assert data["email"] == "etudiant1@est-sale.ma"


def test_verify_invalid_token():
    resp = client.post("/token/verify", json={"token": "token.invalide.ici"})
    assert resp.status_code == 401


def test_verify_empty_token():
    resp = client.post("/token/verify", json={"token": ""})
    assert resp.status_code == 401


# ── Tests /token/refresh ──────────────────────────────────────────────────────

def test_refresh_valid_token():
    from services.jwt import create_refresh_token
    refresh = create_refresh_token({"sub": "user-123", "role": "student"})
    resp = client.post("/token/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_invalid_token():
    resp = client.post("/token/refresh", json={"refresh_token": "mauvais_token"})
    assert resp.status_code == 401


def test_refresh_with_access_token_fails():
    """Un access token ne doit pas être accepté comme refresh token."""
    from services.jwt import create_access_token
    access = create_access_token({"sub": "user-123", "role": "student"})
    resp = client.post("/token/refresh", json={"refresh_token": access})
    assert resp.status_code == 401