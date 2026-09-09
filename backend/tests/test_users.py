import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_can_create_user(client: AsyncClient, test_users, auth_headers):
    admin_headers = auth_headers("admin")
    payload = {
        "name": "New Officer",
        "email": "new.officer@test.gov.in",
        "password": "officerpass123",
        "role": "inspector",
        "region": "Gujarat",
    }
    resp = await client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["email"] == "new.officer@test.gov.in"
    assert resp.json()["data"]["role"] == "inspector"


@pytest.mark.asyncio
async def test_cannot_create_user_with_obsolete_role(client: AsyncClient, test_users, auth_headers):
    admin_headers = auth_headers("admin")

    # Attempt to create reviewer
    rev_payload = {
        "name": "Attempted Reviewer",
        "email": "att.reviewer@test.gov.in",
        "password": "officerpass123",
        "role": "reviewer",
        "region": "Maharashtra",
    }
    resp_rev = await client.post("/api/v1/users", json=rev_payload, headers=admin_headers)
    assert resp_rev.status_code == 422

    # Attempt to create viewer
    view_payload = {
        "name": "Attempted Viewer",
        "email": "att.viewer@test.gov.in",
        "password": "officerpass123",
        "role": "viewer",
        "region": "National",
    }
    resp_view = await client.post("/api/v1/users", json=view_payload, headers=admin_headers)
    assert resp_view.status_code == 422


@pytest.mark.asyncio
async def test_cannot_update_user_to_obsolete_role(client: AsyncClient, test_users, auth_headers):
    admin_headers = auth_headers("admin")
    insp_id = test_users["inspector"].id

    # Attempt to update role to reviewer
    resp = await client.patch(
        f"/api/v1/users/{insp_id}",
        json={"role": "reviewer"},
        headers=admin_headers,
    )
    assert resp.status_code == 422

    # Attempt to update role to viewer
    resp2 = await client.patch(
        f"/api/v1/users/{insp_id}",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_non_admin_cannot_access_users(client: AsyncClient, test_users, auth_headers):
    inspector_headers = auth_headers("inspector")
    resp = await client.get("/api/v1/users", headers=inspector_headers)
    assert resp.status_code == 403
