import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    # 1. Health checks
    h_resp = await client.get("/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "healthy"

    h_api_resp = await client.get("/api/health")
    assert h_api_resp.status_code == 200
    assert h_api_resp.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_statutory_rules_endpoint(client: AsyncClient):
    # 2. Rules
    rules_resp = await client.get("/api/v1/rules")
    assert rules_resp.status_code == 200
    rules = rules_resp.json()["data"]
    assert len(rules) >= 8

@pytest.mark.asyncio
async def test_auth_me_and_scans_authenticated(client: AsyncClient, test_users, auth_headers):
    # 3. Auth Me
    admin_headers = auth_headers("admin")
    me_resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["role"] == "admin"

    # 4. Scans list
    scans_resp = await client.get("/api/v1/scans", headers=admin_headers)
    assert scans_resp.status_code == 200
    assert "data" in scans_resp.json()
