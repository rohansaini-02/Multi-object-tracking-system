"""
Core Cryptographic & Security Utilities (Backend Core Module).

Provides password hashing and verification using PyCA bcrypt bindings (with hashlib PBKDF2 fallback),
and signed JWT access token creation and decoding algorithms. Bypasses legacy passlib bugs.

Architectural Role:
- Service & Security Layer helper.
- Enforces 72-byte truncation boundary for bcrypt password compatibility.
- Implements stateless JWT authentication token protocol for FastAPI dependencies.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import hashlib
import hmac
import os
import jwt

try:
    import bcrypt
except ImportError:
    bcrypt = None  # type: ignore

from backend.app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify candidate plain-text password against a stored hash string.

    Args:
        plain_password: Candidate password string provided during login.
        hashed_password: Standard bcrypt hash string stored in the database.

    Returns:
        True if plain_password matches the hashed_password, False otherwise.

    Notes:
        Truncates candidate password to 72 bytes before verification to comply with
        the maximum input length constraint of the Blowfish/bcrypt algorithm.
    """
    try:
        pwd_bytes = plain_password.encode("utf-8")
        if len(pwd_bytes) > 72:
            pwd_bytes = pwd_bytes[:72]

        if bcrypt is not None and hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            hash_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(pwd_bytes, hash_bytes)

        # Fallback for PBKDF2 hashes (pbkdf2_sha256$iterations$salt$hash)
        if hashed_password.startswith("pbkdf2_sha256$"):
            parts = hashed_password.split("$")
            if len(parts) == 4:
                iterations = int(parts[1])
                salt = parts[2].encode("utf-8")
                expected_hash = parts[3]
                computed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt, iterations).hex()
                return hmac.compare_digest(computed, expected_hash)

        return False
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Generate a salt and compute a secure bcrypt (or PBKDF2) hash for a plain-text password.

    Args:
        password: Plain-text password string supplied during registration.

    Returns:
        Encoded hash string containing algorithm prefix, cost factor, salt, and checksum.

    Notes:
        - Uses default bcrypt cost factor (12) balancing security against computation overhead.
        - Truncates raw UTF-8 encoded bytes to 72 bytes to prevent overflow errors.
    """
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]

    if bcrypt is not None:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

    # PBKDF2 SHA-256 fallback if bcrypt C extension is unavailable in environment
    iterations = 100000
    salt_bytes = os.urandom(16)
    salt_str = salt_bytes.hex()
    computed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt_str}${computed}"


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Construct and sign a PyJWT bearer access token for a given user subject.

    Args:
        subject: User identifier string (e.g. user UUID) stored in the token 'sub' claim.
        expires_delta: Optional custom token lifetime duration. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Signed JWT string formatted with header, payload, and HS256 signature.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode, verify signature, and validate expiration of a JWT access token.

    Args:
        token: Raw JWT string extracted from the HTTP Authorization header.

    Returns:
        Decoded payload dictionary if token is valid and non-expired; None if signature or claims fail.

    Raises:
        Does not raise exceptions; returns None for callers to issue HTTP 401 response.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        return None
