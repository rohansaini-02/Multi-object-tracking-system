"""
Unit and Integration Tests for Standalone Google Authentication Module.
Validates cryptographic verification, session management, logout, and API endpoints.
"""

import time
import json
import base64
import pytest
from fastapi.testclient import TestClient

from modules.google_auth.config import config
from modules.google_auth.verifier import (
    GoogleTokenVerifier,
    InvalidTokenError,
    ExpiredTokenError,
    InvalidAudienceError,
    EmailNotVerifiedError,
)
from modules.google_auth.session import SessionManager
from modules.google_auth.models import GoogleUserProfile
from modules.google_auth.app import app


def create_test_jwt(claims: dict) -> str:
    """Helper to craft base64-encoded JWT structures for deterministic testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    signature_b64 = base64.urlsafe_b64encode(b"simulated-test-signature-bytes").decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{signature_b64}"


@pytest.fixture
def verifier():
    return GoogleTokenVerifier(client_id=config.GOOGLE_CLIENT_ID)


@pytest.fixture
def session_mgr():
    mgr = SessionManager()
    mgr.clear_revocations()
    return mgr


@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# 1. TOKEN VERIFIER TESTS
# ============================================================================

def test_verifier_valid_token(verifier):
    """Verify that a valid token correctly decodes all profile fields."""
    now = int(time.time())
    token = create_test_jwt({
        "iss": "mock-google-test",
        "sub": "google-user-12345",
        "email": "developer@example.com",
        "name": "Jane Developer",
        "given_name": "Jane",
        "family_name": "Developer",
        "picture": "https://example.com/avatar.jpg",
        "email_verified": True,
        "aud": config.GOOGLE_CLIENT_ID,
        "exp": now + 3600,
    })

    profile = verifier.verify_token(token)
    assert profile.sub == "google-user-12345"
    assert profile.email == "developer@example.com"
    assert profile.name == "Jane Developer"
    assert profile.picture == "https://example.com/avatar.jpg"
    assert profile.email_verified is True


def test_verifier_expired_token(verifier):
    """Verify that expired tokens are strictly rejected."""
    past = int(time.time()) - 3600
    token = create_test_jwt({
        "iss": "mock-google-test",
        "sub": "google-user-12345",
        "email": "developer@example.com",
        "aud": config.GOOGLE_CLIENT_ID,
        "exp": past,
    })

    with pytest.raises(ExpiredTokenError):
        verifier.verify_token(token)


def test_verifier_invalid_audience(verifier):
    """Verify that tokens intended for other client IDs are rejected."""
    now = int(time.time())
    token = create_test_jwt({
        "iss": "mock-google-test",
        "sub": "google-user-12345",
        "email": "developer@example.com",
        "aud": "malicious-foreign-client-id.apps.googleusercontent.com",
        "exp": now + 3600,
    })

    with pytest.raises(InvalidAudienceError):
        verifier.verify_token(token)


def test_verifier_unverified_email(verifier):
    """Verify that Google accounts without email verification are rejected."""
    now = int(time.time())
    token = create_test_jwt({
        "iss": "mock-google-test",
        "sub": "google-user-12345",
        "email": "unverified@example.com",
        "email_verified": False,
        "aud": config.GOOGLE_CLIENT_ID,
        "exp": now + 3600,
    })

    with pytest.raises(EmailNotVerifiedError):
        verifier.verify_token(token)


def test_verifier_malformed_token(verifier):
    """Verify that completely corrupted tokens raise InvalidTokenError."""
    with pytest.raises(InvalidTokenError):
        verifier.verify_token("not-a-valid-jwt")


# ============================================================================
# 2. SESSION & REVOCATION TESTS
# ============================================================================

def test_session_lifecycle(session_mgr):
    """Verify session creation, verification, and revocation (logout)."""
    user = GoogleUserProfile(
        sub="google-user-999",
        email="test@example.com",
        name="Test User",
        email_verified=True,
    )

    # 1. Create Session
    session_data = session_mgr.create_session(user)
    assert "access_token" in session_data
    token = session_data["access_token"]

    # 2. Verify Session
    claims = session_mgr.verify_session(token)
    assert claims is not None
    assert claims["sub"] == "google-user-999"
    assert claims["email"] == "test@example.com"

    # 3. Revoke Session (Logout)
    revoked = session_mgr.revoke_session(token)
    assert revoked is True

    # 4. Verification after logout must fail
    claims_after_logout = session_mgr.verify_session(token)
    assert claims_after_logout is None


# ============================================================================
# 3. FASTAPI ENDPOINT INTEGRATION TESTS
# ============================================================================

def test_api_config_endpoint(client):
    """Test public config endpoint returns current Client ID."""
    res = client.get("/auth/config")
    assert res.status_code == 200
    data = res.json()
    assert data["client_id"] == config.GOOGLE_CLIENT_ID


def test_api_google_login_success(client):
    """Test /auth/google full handshake with valid token."""
    now = int(time.time())
    valid_token = create_test_jwt({
        "iss": "mock-google-test",
        "sub": "google-user-777",
        "email": "alice@gmail.com",
        "name": "Alice Smith",
        "picture": "https://lh3.googleusercontent.com/avatar",
        "email_verified": True,
        "aud": config.GOOGLE_CLIENT_ID,
        "exp": now + 3600,
    })

    res = client.post("/auth/google", json={"credential": valid_token})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@gmail.com"
    assert data["user"]["sub"] == "google-user-777"


def test_api_google_login_expired_rejection(client):
    """Test /auth/google rejects expired token with HTTP 401."""
    past = int(time.time()) - 3600
    expired_token = create_test_jwt({
        "iss": "mock-google-test",
        "sub": "google-user-777",
        "email": "alice@gmail.com",
        "aud": config.GOOGLE_CLIENT_ID,
        "exp": past,
    })

    res = client.post("/auth/google", json={"credential": expired_token})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_api_protected_profile_and_logout(client):
    """Test complete flow: Login -> Access /auth/me -> Logout -> Denied /auth/me."""
    now = int(time.time())
    token_str = create_test_jwt({
        "iss": "mock-google-test",
        "sub": "google-user-888",
        "email": "bob@gmail.com",
        "name": "Bob Builder",
        "email_verified": True,
        "aud": config.GOOGLE_CLIENT_ID,
        "exp": now + 3600,
    })

    # 1. Login
    login_res = client.post("/auth/google", json={"credential": token_str})
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Access /auth/me (Authorized)
    me_res = client.get("/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "bob@gmail.com"

    # 3. Logout
    logout_res = client.post("/auth/logout", headers=auth_headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "success"

    # 4. Access /auth/me after Logout (Must be Rejected)
    me_after_res = client.get("/auth/me", headers=auth_headers)
    assert me_after_res.status_code == 401
    assert "revoked" in me_after_res.json()["detail"].lower()


def test_api_callback_endpoint(client):
    """Test OAuth redirect callback endpoint."""
    res = client.get("/auth/google/callback?code=4/0AbcDeFgHiJkLmNo&state=xyz123")
    assert res.status_code == 200
    assert res.json()["status"] == "code_received"
