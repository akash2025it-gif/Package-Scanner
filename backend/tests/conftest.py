import asyncio
import os
import sys
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_FILE = "./test_packcheck.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

# Set test environment
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"
os.environ["OCR_PROVIDER"] = "mock"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "./test_uploads"

import io
from PIL import Image, ImageDraw

def create_clear_test_image_bytes(width: int = 600, height: int = 800) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw crisp grid pattern and high contrast text to ensure high Laplacian variance
    for x in range(0, width, 25):
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0), width=2)
    for y in range(0, height, 25):
        draw.line([(0, y), (width, y)], fill=(0, 0, 0), width=2)
    draw.rectangle([(50, 50), (width - 50, height - 50)], outline=(0, 0, 0), width=3)
    draw.text((60, 60), "LEGAL METROLOGY PACKAGING LABEL", fill=(0, 0, 0))
    draw.text((60, 100), "MRP: Rs. 150.00 (Incl. of all taxes)", fill=(0, 0, 0))
    draw.text((60, 140), "Net Quantity: 500 g", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import User, Product, Scan, ScanImage, Declaration, ComplianceReport, AuditLog

# Test async engine pointing to shared file
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_users(db_session: AsyncSession):
    admin = User(
        id="user-admin-1",
        name="Admin Test",
        email="admin@test.gov.in",
        password_hash=hash_password("admin123"),
        role="admin",
        region="HQ",
        is_active=True,
    )
    inspector = User(
        id="user-insp-1",
        name="Inspector Test",
        email="inspector@test.gov.in",
        password_hash=hash_password("inspector123"),
        role="inspector",
        region="Delhi NCR",
        is_active=True,
    )
    legacy_reviewer = User(
        id="user-rev-1",
        name="Reviewer Test (Legacy)",
        email="reviewer.patel@packcheck.gov.in",
        password_hash=hash_password("reviewer123"),
        role="reviewer",
        region="Maharashtra",
        is_active=False,
    )
    legacy_viewer = User(
        id="user-view-1",
        name="Viewer Test (Legacy)",
        email="viewer@packcheck.gov.in",
        password_hash=hash_password("viewer123"),
        role="viewer",
        region="National",
        is_active=False,
    )
    db_session.add_all([admin, inspector, legacy_reviewer, legacy_viewer])
    await db_session.commit()

    return {
        "admin": admin,
        "inspector": inspector,
        "reviewer": legacy_reviewer,
        "viewer": legacy_viewer,
    }


@pytest.fixture
def auth_headers(test_users):
    def _headers_for(role: str):
        user = test_users.get(role)
        if not user:
            token = create_access_token(subject="unknown-user", role=role)
            return {"Authorization": f"Bearer {token}"}
        token = create_access_token(subject=user.id, role=user.role)
        return {"Authorization": f"Bearer {token}"}
    return _headers_for


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_files():
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
    if os.path.exists("./test_uploads"):
        import shutil
        try:
            shutil.rmtree("./test_uploads")
        except Exception:
            pass
