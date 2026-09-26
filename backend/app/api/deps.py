"""
FastAPI Dependency Injection Providers (Backend API Infrastructure Tier).

Provides reusable dependencies for request-scoped database sessions (`get_db_session`)
and authenticated user identity resolution (`get_current_user`).

Architectural Role:
- Intercepts incoming HTTP requests, decodes OAuth2 bearer tokens, and validates user sessions.
- Ensures database sessions are isolated per request thread and cleanly disposed.
"""

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import decode_access_token
from backend.app.db import database
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency injecting an async SQLAlchemy database session.

    Yields:
        AsyncSession connected to database pool.

    Notes:
        Ensures strict cleanup via `finally` block to return session to pool.
    """
    async with database.AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    FastAPI dependency resolving current authenticated User entity from JWT bearer token.

    Args:
        token: Raw JWT string automatically extracted from Authorization header.
        session: Injected request database session context.

    Returns:
        User entity corresponding to the decoded token subject.

    Raises:
        HTTPException 401 Unauthorized: If token is missing, invalid, expired, or user is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user
