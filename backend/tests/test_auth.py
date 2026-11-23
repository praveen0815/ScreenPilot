import pytest

from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_access_token, decode_access_token
from app.db.enums import UserRole


def test_password_hash_roundtrip():
    digest = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", digest)
    assert not verify_password("wrong-password", digest)


def test_access_token_roundtrip():
    from uuid import uuid4

    user_id = uuid4()
    token, _expires = create_access_token(user_id, UserRole.USER)
    claims = decode_access_token(token)
    assert claims.user_id == user_id
    assert claims.role is UserRole.USER


@pytest.mark.asyncio
async def test_register_login_and_profile(sqlite_app_client):
    client = sqlite_app_client

    register = client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "valid-passphrase-1",
            "display_name": "Owner",
        },
    )
    assert register.status_code == 201
    tokens = register.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    profile = client.get("/api/users/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "owner@example.com"

    login = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "valid-passphrase-1"},
    )
    assert login.status_code == 200

    refresh = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]


@pytest.mark.asyncio
async def test_duplicate_email_conflict(sqlite_app_client):
    client = sqlite_app_client
    payload = {
        "email": "dup@example.com",
        "password": "valid-passphrase-1",
        "display_name": "Dup",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    conflict = client.post("/api/auth/register", json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_protected_route_requires_auth(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"