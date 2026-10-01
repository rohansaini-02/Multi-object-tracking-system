"""
Unit Test Suite for Week 6 FastAPI Backend Foundation (Auth, Security & Video Upload).

Tests password hashing, JWT token generation/validation, file format validation, and storage rules.
"""

import io
import pytest
from fastapi import HTTPException

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from backend.app.services.video_service import ALLOWED_EXTENSIONS, VideoService


def test_password_hashing_and_verification():
    """Verify bcrypt password hashing and candidate verification."""
    plain_password = "SecretPassword123!"
    hashed = get_password_hash(plain_password)

    assert hashed != plain_password
    assert verify_password(plain_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_create_and_decode():
    """Verify JWT access token creation and decoding payload."""
    user_id = "user-1234-uuid"
    token = create_access_token(subject=user_id)

    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == user_id


def test_jwt_token_invalid_decode():
    """Verify decode_access_token returns None for tampered or invalid tokens."""
    invalid_token = "invalid.jwt.token.string"
    payload = decode_access_token(invalid_token)
    assert payload is None


def test_allowed_extensions_contain_mp4_and_avi():
    """Verify PRD FR-01 required video formats are allowed."""
    assert ".mp4" in ALLOWED_EXTENSIONS
    assert ".avi" in ALLOWED_EXTENSIONS
    assert ".mov" in ALLOWED_EXTENSIONS
    assert ".mkv" in ALLOWED_EXTENSIONS


@pytest.mark.asyncio
async def test_video_service_rejects_disallowed_extension():
    """Verify UploadFile with disallowed extension (e.g. .txt, .exe) raises 422 HTTP exception."""
    class DummyUploadFile:
        def __init__(self, filename: str):
            self.filename = filename

    dummy_file = DummyUploadFile(filename="malicious_script.exe")
    service = VideoService(video_repo=None)  # Repo not called since validation fails early

    with pytest.raises(HTTPException) as exc_info:
        await service.upload_video(dummy_file, user_id="user-123")

    assert exc_info.value.status_code == 422
    assert "Unsupported file format" in exc_info.value.detail
