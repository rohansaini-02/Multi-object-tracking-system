"""
Configuration settings for the Standalone Google Auth Module.
"""

import os
from typing import List

# Fix corrupted Windows machine-level CA bundle paths (e.g. non-existent PostgreSQL ca-bundle.crt)
for ca_var in ("CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
    ca_val = os.environ.get(ca_var)
    if ca_val and not os.path.isfile(ca_val):
        os.environ.pop(ca_var, None)


class GoogleAuthConfig:
    """Isolated configuration settings for Google OAuth & session management."""

    # Google OAuth 2.0 Credentials (loaded from environment variables)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Valid Google Token Issuers
    VALID_ISSUERS: List[str] = [
        "accounts.google.com",
        "https://accounts.google.com",
    ]

    # Session token signing key (independent secret for this module)
    SESSION_SECRET_KEY: str = os.getenv(
        "SESSION_SECRET_KEY",
        "standalone-google-auth-secret-key-32890578921479812",
    )
    SESSION_ALGORITHM: str = "HS256"
    SESSION_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Standalone Test Server Settings
    STANDALONE_HOST: str = "127.0.0.1"
    STANDALONE_PORT: int = 8088


config = GoogleAuthConfig()
