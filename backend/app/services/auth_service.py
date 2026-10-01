"""
Authentication Service (Backend Application Business Logic Tier).

Coordinates user account registration and login authentication workflows.
Coordinates between `UserRepository` for data persistence and `security.py` for
bcrypt password hashing and signed JWT token issuance.

Architectural Role:
- Enforces user email uniqueness during registration.
- Verifies plain-text credentials against stored bcrypt password hashes.
- Generates stateless OAuth2 compatible JWT bearer tokens upon authentication.
"""

from fastapi import HTTPException, status
from backend.app.core.security import get_password_hash, verify_password, create_access_token
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import UserCreate, Token, UserResponse


class AuthService:
    """
    Business service executing user registration and login credential verification.
    """

    def __init__(self, user_repo: UserRepository):
        """
        Args:
            user_repo: Injected UserRepository instance for database query operations.
        """
        self.user_repo = user_repo

    async def register(self, user_in: UserCreate) -> UserResponse:
        """
        Register a new user after validating email uniqueness and computing bcrypt password hash.

        Args:
            user_in: User registration data DTO containing email, password, and optional full name.

        Returns:
            UserResponse DTO representing the newly created user profile.

        Raises:
            HTTPException 409 Conflict: If an account with the specified email address already exists.
        """
        existing = await self.user_repo.get_by_email(user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists.",
            )

        hashed_pwd = get_password_hash(user_in.password)
        user = await self.user_repo.create(
            email=user_in.email,
            hashed_password=hashed_pwd,
            full_name=user_in.full_name,
        )
        return UserResponse.model_validate(user)

    async def login(self, email: str, password: str) -> Token:
        """
        Authenticate candidate credentials and issue a signed JWT access token.

        Args:
            email: User's registered email address string.
            password: Candidate plain text password string.

        Returns:
            Token DTO containing JWT access token string and token type ('bearer').

        Raises:
            HTTPException 401 Unauthorized: If email is not found or password verification fails.
        """
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_str = create_access_token(subject=user.id)
        return Token(access_token=token_str, token_type="bearer")
