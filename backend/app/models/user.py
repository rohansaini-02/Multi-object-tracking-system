"""
User Domain ORM Model (Backend Data Layer Tier).

Defines the database entity schema for system user accounts, authentication credentials,
and dynamic relationships to user-owned video assets and multi-object tracking jobs.
"""

import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base

if TYPE_CHECKING:
    from backend.app.models.video import Video
    from backend.app.models.tracking_job import TrackingJob


class User(Base):
    """
    SQLAlchemy ORM entity representing a registered system user.

    Attributes:
        id: Primary key UUID string (36 chars).
        email: Unique lowercased email address used for login authentication.
        hashed_password: Encoded bcrypt password digest string.
        full_name: Optional display name for the account holder.
        is_active: Boolean flag indicating if user account is enabled.
        created_at: ISO-8601 UTC timestamp of registration.
        videos: Cascading one-to-many relationship to uploaded Video assets.
        tracking_jobs: Cascading one-to-many relationship to submitted TrackingJobs.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    tracking_jobs: Mapped[List["TrackingJob"]] = relationship("TrackingJob", back_populates="user", cascade="all, delete-orphan")
