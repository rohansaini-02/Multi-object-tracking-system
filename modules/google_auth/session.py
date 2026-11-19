"""
Independent Session and JWT Token Management for Google Authentication.
"""

from typing import Optional, Dict, Any, Set
from datetime import datetime, timedelta, timezone
import uuid
import jwt

from modules.google_auth.config import config
from modules.google_auth.models import GoogleUserProfile


class SessionManager:
    """Manages creation, verification, and revocation of user sessions."""

    def __init__(self):
        self.secret_key = config.SESSION_SECRET_KEY
        self.algorithm = config.SESSION_ALGORITHM
        self.expire_minutes = config.SESSION_EXPIRE_MINUTES
        # Blacklist of revoked session IDs (e.g., after explicit logout)
        self._revoked_sessions: Set[str] = set()

    def create_session(self, user: GoogleUserProfile) -> Dict[str, Any]:
        """
        Issue a signed session JWT token for the verified user.

        Args:
            user: Verified Google user profile.

        Returns:
            Dictionary containing access_token, token_type, expires_in_seconds, and user.
        """
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.expire_minutes)
        expire_time = now + expires_delta
        session_id = str(uuid.uuid4())

        payload = {
            "sub": user.sub,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "jti": session_id,
            "iat": int(now.timestamp()),
            "exp": int(expire_time.timestamp()),
            "iss": "mot-google-auth-module",
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in_seconds": int(expires_delta.total_seconds()),
            "session_id": session_id,
        }

    def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session token. Checks signature, expiry, and revocation blacklist.

        Args:
            token: Raw Bearer JWT string.

        Returns:
            Decoded payload dict if valid, or None if invalid/expired/revoked.
        """
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            # Check if session has been revoked
            session_id = payload.get("jti")
            if session_id and session_id in self._revoked_sessions:
                return None

            return payload
        except (jwt.PyJWTError, Exception):
            return None

    def revoke_session(self, token: str) -> bool:
        """
        Revoke an active session token (Logout).

        Args:
            token: Raw Bearer JWT string to blacklist.

        Returns:
            True if session was parsed and added to revocation blacklist.
        """
        try:
            # Decode without strict expiration to allow revoking even slightly stale tokens
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            session_id = payload.get("jti")
            if session_id:
                self._revoked_sessions.add(session_id)
                return True
        except Exception:
            pass
        return False

    def clear_revocations(self) -> None:
        """Clear revocation blacklist (used primarily for test cleanup)."""
        self._revoked_sessions.clear()


session_manager = SessionManager()
