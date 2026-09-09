import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@test.gov.in", "password": "inspector123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["user"]["role"] == "inspector"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@test.gov.in", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, test_users, auth_headers):
    headers = auth_headers("inspector")
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "inspector@test.gov.in"


@pytest.mark.asyncio
async def test_unauthorized_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
