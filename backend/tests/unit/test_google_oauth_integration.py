"""
Integration test for Google OAuth in the primary FastAPI tracking application.
Validates POST /api/v1/auth/google, user upsertion, and JWT token issuance using an isolated SQLite test database.
"""

import time
import json
import base64
import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.deps import get_db_session
from backend.app.db.database import Base
from backend.app.core.config import settings
import backend.app.models  # noqa: F401


# Configure dedicated isolated in-memory test database
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def override_get_db_session():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db_session] = override_get_db_session


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    async def init_models():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    yield
    async def drop_models():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(drop_models())


def create_test_google_jwt(claims: dict) -> str:
    """Craft a base64-encoded JWT structure for deterministic testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    signature_b64 = base64.urlsafe_b64encode(b"simulated-test-signature-bytes").decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{signature_b64}"


@pytest.fixture
def client():
    return TestClient(app)


def test_google_login_flow_in_main_app(client):
    """Verify that POST /api/v1/auth/google creates user and returns application JWT."""
    now = int(time.time())
    unique_email = f"google.user.{now}@example.com"
    token = create_test_google_jwt({
        "iss": "mock-google-test",
        "sub": f"google-uid-{now}",
        "email": unique_email,
        "name": "Google Test User",
        "picture": "https://lh3.googleusercontent.com/avatar.jpg",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "exp": now + 3600,
    })

    # 1. First sign in with Google
    res = client.post("/api/v1/auth/google", json={"credential": token})
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    access_token = data["access_token"]

    # 2. Verify identity via /api/v1/auth/me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200, me_res.text
    user_data = me_res.json()
    assert user_data["email"] == unique_email
    assert user_data["full_name"] == "Google Test User"
    assert user_data["avatar_url"] == "https://lh3.googleusercontent.com/avatar.jpg"
    assert user_data["auth_provider"] == "google"

    # 3. Second sign in (Account linking / Idempotency)
    second_res = client.post("/api/v1/auth/google", json={"credential": token})
    assert second_res.status_code == 200, second_res.text
    assert "access_token" in second_res.json()


def test_google_login_expired_token_rejected(client):
    """Verify that POST /api/v1/auth/google rejects expired tokens with 401."""
    past = int(time.time()) - 3600
    expired_token = create_test_google_jwt({
        "iss": "mock-google-test",
        "sub": "google-uid-expired",
        "email": "expired@example.com",
        "aud": settings.GOOGLE_CLIENT_ID,
        "exp": past,
    })

    res = client.post("/api/v1/auth/google", json={"credential": expired_token})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()
