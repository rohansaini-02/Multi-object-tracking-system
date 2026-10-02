"""
Authentication & Authorization API Presentation Router (Backend API Layer Tier).

Exposes HTTP REST endpoints for user registration, OAuth2 password grant login,
and authenticated identity resolution (`/auth/me`).

Architectural Role:
- Handles request parsing and parameter validation via Pydantic schemas (`UserCreate`, `UserLogin`, `Token`).
- Delegates business logic execution to `AuthService`.
- Manages transaction contexts passed via SQLAlchemy `AsyncSession` dependencies.
"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import Token, UserCreate, UserResponse
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Register a new user account with hashed password credentials.

    Args:
        user_in: Pydantic UserCreate payload containing email, password, and full name.
        session: Injected async database session transaction context.

    Returns:
        UserResponse schema excluding sensitive credential fields.

    Raises:
        HTTPException 409 Conflict: If an account with the specified email already exists.
    """
    user_repo = UserRepository(session)
    service = AuthService(user_repo)
    return await service.register(user_in)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> Token:
    """
    Authenticate user credentials via OAuth2 password grant and issue a signed JWT access token.

    Args:
        form_data: Standard OAuth2 form payload containing username (email) and password.
        session: Injected async database session transaction context.

    Returns:
        Token schema containing access_token string and token_type ('bearer').

    Raises:
        HTTPException 401 Unauthorized: If email or password candidate is invalid.
    """
    user_repo = UserRepository(session)
    service = AuthService(user_repo)
    return await service.login(email=form_data.username, password=form_data.password)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """
    Fetch identity details for the currently authenticated user session.

    Args:
        current_user: Authenticated User entity resolved from JWT bearer token dependency.

    Returns:
        UserResponse schema representing the current user profile.
    """
    return UserResponse.model_validate(current_user)
