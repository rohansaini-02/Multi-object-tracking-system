"""
Video Domain ORM Model (Backend Data Layer Tier).

Defines the database entity schema for user-uploaded video assets and extracted OpenCV metadata.
Includes composite index optimization (`idx_videos_user_created`) for fast user timeline pagination.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.tracking_job import TrackingJob


class Video(Base):
    """
    SQLAlchemy ORM entity representing an uploaded video clip asset.

    Attributes:
        id: Primary key UUID string (36 chars).
        user_id: Foreign key referencing the owning User record.
        filename: Original user filename.
        file_path: Absolute or relative disk path where binary video file is stored.
        file_size: Size of video file in bytes.
        duration: Duration of video clip in seconds.
        fps: Frame rate of video stream in frames per second.
        width: Frame width dimension in pixels.
        height: Frame height dimension in pixels.
        frame_count: Total frame count in the video stream.
        created_at: ISO-8601 UTC upload timestamp.
        user: Relationship back to owning User instance.
        tracking_jobs: Cascading relationship to execution jobs associated with this video.
    """

    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frame_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="videos")
    tracking_jobs: Mapped[List["TrackingJob"]] = relationship("TrackingJob", back_populates="video", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_videos_user_created", "user_id", "created_at"),
    )
