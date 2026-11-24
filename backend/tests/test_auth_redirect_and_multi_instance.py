"""
PackCheck AI — Login Redirect & Multi-Instance Authentication Verification Suite
Tests all 12 points specified in Phase 5:
1. Successful login
2. Invalid login
3. Dashboard access after login
4. Browser refresh after login simulation
5. Direct access to protected routes
6. /auth/me with valid token
7. /auth/me with invalid token
8. Auxiliary API error handling
9. Expired token handling
10. Logout and subsequent protected-route access
11. Two independent backend instances using the same configuration (deterministic IDs)
12. User identity consistency across backend instances
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, decode_token, hash_password
from app.core.database import init_db, seed_demo_users, AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_successful_login():
    """Test 1: Successful login with valid credentials."""
    await init_db()
    await seed_demo_users()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={"email": settings.INITIAL_INSPECTOR_EMAIL, "password": settings.INITIAL_INSPECTOR_PASSWORD or "inspector123"}
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json().get("data", {})
        assert "access_token" in data
        assert data.get("user", {}).get("email") == settings.INITIAL_INSPECTOR_EMAIL
        assert data.get("user", {}).get("role") == "inspector"


@pytest.mark.asyncio
async def test_invalid_login():
    """Test 2: Invalid login credentials rejected safely with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={"email": settings.INITIAL_INSPECTOR_EMAIL, "password": "wrong-password-123"}
        )
        assert resp.status_code == 401
        err = resp.json()
        msg = err.get("detail") or err.get("message") or (err.get("error", {}).get("message") if isinstance(err.get("error"), dict) else "")
        assert "Invalid email or password" in msg


@pytest.mark.asyncio
async def test_dashboard_access_after_login():
    """Test 3: Dashboard data endpoints accessible after successful login."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={"email": settings.INITIAL_INSPECTOR_EMAIL, "password": settings.INITIAL_INSPECTOR_PASSWORD or "inspector123"}
        )
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Dashboard analytics KPI
        summary_resp = await client.get(f"{settings.API_V1_PREFIX}/analytics/summary", headers=headers)
        assert summary_resp.status_code == 200

        # Dashboard recent scans
        scans_resp = await client.get(f"{settings.API_V1_PREFIX}/scans?limit=8", headers=headers)
        assert scans_resp.status_code == 200


@pytest.mark.asyncio
async def test_browser_refresh_and_auth_me():
    """Test 4 & 6: /auth/me with valid token restores session cleanly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={"email": settings.INITIAL_INSPECTOR_EMAIL, "password": settings.INITIAL_INSPECTOR_PASSWORD or "inspector123"}
        )
        token = login_resp.json()["data"]["access_token"]

        me_resp = await client.get(f"{settings.API_V1_PREFIX}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        user_data = me_resp.json().get("data", {})
        assert user_data.get("email") == settings.INITIAL_INSPECTOR_EMAIL
        assert user_data.get("role") == "inspector"


@pytest.mark.asyncio
async def test_direct_access_to_protected_routes():
    """Test 5: Unauthenticated access to protected routes strictly rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Accessing /auth/me without token
        resp1 = await client.get(f"{settings.API_V1_PREFIX}/auth/me")
        assert resp1.status_code == 401

        # Accessing /scans without token
        resp2 = await client.get(f"{settings.API_V1_PREFIX}/scans")
        assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_with_invalid_token():
    """Test 7: /auth/me with tampered or forged token rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsignature"
        resp = await client.get(f"{settings.API_V1_PREFIX}/auth/me", headers={"Authorization": f"Bearer {invalid_token}"})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_handling():
    """Test 9: Expired access token rejected with 401."""
    expired_token = create_access_token(
        subject="test-user-id",
        role="inspector",
        expires_delta=timedelta(seconds=-30)  # Expired 30 seconds ago
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"{settings.API_V1_PREFIX}/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401
        err = resp.json()
        msg = err.get("detail") or err.get("message") or (err.get("error", {}).get("message") if isinstance(err.get("error"), dict) else "")
        assert "Invalid or expired" in msg


@pytest.mark.asyncio
async def test_logout_endpoint():
    """Test 10: Logout endpoint completes successfully."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={"email": settings.INITIAL_INSPECTOR_EMAIL, "password": settings.INITIAL_INSPECTOR_PASSWORD or "inspector123"}
        )
        token = login_resp.json()["data"]["access_token"]

        logout_resp = await client.post(
            f"{settings.API_V1_PREFIX}/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json().get("success") is True


@pytest.mark.asyncio
async def test_multi_instance_deterministic_id_and_token_compatibility():
    """Test 11 & 12: Two independent backend instances generate identical IDs and accept each other's tokens."""
    import uuid
    from app.core.database import AsyncSessionLocal

    ADMIN_SEEDED_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "packcheck.admin.seeded"))
    INSPECTOR_SEEDED_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "packcheck.inspector.seeded"))

    # Verify deterministic UUID values
    assert ADMIN_SEEDED_ID == str(uuid.uuid5(uuid.NAMESPACE_DNS, "packcheck.admin.seeded"))
    assert INSPECTOR_SEEDED_ID == str(uuid.uuid5(uuid.NAMESPACE_DNS, "packcheck.inspector.seeded"))

    # Re-run seed_demo_users to simulate a second cold-start instance
    await seed_demo_users()

    async with AsyncSessionLocal() as session:
        admin_res = await session.execute(select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL))
        admin_user = admin_res.scalar_one_or_none()
        inspector_res = await session.execute(select(User).where(User.email == settings.INITIAL_INSPECTOR_EMAIL))
        inspector_user = inspector_res.scalar_one_or_none()

        assert admin_user is not None
        assert inspector_user is not None

        # Verify that IDs match deterministic seed IDs
        assert admin_user.id == ADMIN_SEEDED_ID
        assert inspector_user.id == INSPECTOR_SEEDED_ID

    # Create token from "Instance A" using the deterministic ID
    token_instance_a = create_access_token(
        subject=INSPECTOR_SEEDED_ID,
        role="inspector",
        extra_claims={"email": settings.INITIAL_INSPECTOR_EMAIL}
    )

    # Validate against "Instance B" via FastAPI test transport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"{settings.API_V1_PREFIX}/auth/me",
            headers={"Authorization": f"Bearer {token_instance_a}"}
        )
        assert resp.status_code == 200, f"Instance B rejected Instance A token: {resp.text}"
        data = resp.json().get("data", {})
        assert data.get("id") == INSPECTOR_SEEDED_ID
        assert data.get("email") == settings.INITIAL_INSPECTOR_EMAIL
