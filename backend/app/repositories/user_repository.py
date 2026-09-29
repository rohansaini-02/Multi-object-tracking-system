"""
User Repository Data Access Layer (Backend Persistence Tier).

Encapsulates direct SQLAlchemy ORM queries and database CRUD operations for User entities.

Architectural Role:
- Isolates SQL execution logic from high-level application services.
- Executes parameterized queries via AsyncSession.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User


class UserRepository:
    """
    Data access repository managing database operations for User records.
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: Active request-scoped AsyncSession instance.
        """
        self.session = session

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Query a User record by primary key UUID.

        Args:
            user_id: Unique UUID string of the target user.

        Returns:
            User entity instance or None if not found.
        """
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Query a User record by lowercased unique email address.

        Args:
            email: Raw or lowercased email string.

        Returns:
            User entity instance or None if not found.
        """
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, email: str, hashed_password: str, full_name: Optional[str] = None) -> User:
        """
        Persist a new User record into the database.

        Args:
            email: Lowercased email address.
            hashed_password: Encoded bcrypt password digest string.
            full_name: Optional user display name.

        Returns:
            Newly created and refreshed User ORM instance.
        """
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
