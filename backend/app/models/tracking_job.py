"""
TrackingJob Domain ORM Model (Backend Data Layer Tier).

Defines the state machine, execution configuration, progress status, and relationships
for background DeepSORT tracking jobs. Supports asynchronous Redis RQ queue processing.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.video import Video
    from backend.app.models.track_result import TrackResult
    from backend.app.models.mot17_evaluation import MOT17Evaluation


class JobStatus(str, enum.Enum):
    """
    Lifecycle status enumeration for background tracking tasks.

    States:
        QUEUED: Task created and waiting in background job queue.
        PROCESSING: Worker actively running DeepSORT tracking pipeline.
        COMPLETED: Execution finished successfully; track results stored.
        FAILED: Execution encountered an unhandled exception or error.
    """
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TrackingJob(Base):
    """
    SQLAlchemy ORM entity tracking asynchronous tracking job executions.

    Attributes:
        id: Primary key UUID string (36 chars).
        video_id: Foreign key referencing target Video entity.
        user_id: Foreign key referencing requesting User entity.
        status: JobStatus lifecycle enum value (QUEUED, PROCESSING, COMPLETED, FAILED).
        progress: Execution progress percentage integer (0 to 100).
        config: Custom hyperparameter dictionary (conf_threshold, max_cosine_distance, etc.).
        error_message: Detailed exception string if job failed; None otherwise.
        created_at: ISO-8601 UTC job submission timestamp.
        updated_at: ISO-8601 UTC last status update timestamp.
    """

    __tablename__ = "tracking_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="jobstatus"), default=JobStatus.QUEUED, nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tracking_jobs")
    video: Mapped["Video"] = relationship("Video", back_populates="tracking_jobs")
    track_result: Mapped[Optional["TrackResult"]] = relationship("TrackResult", back_populates="tracking_job", uselist=False, cascade="all, delete-orphan")
    mot17_evaluation: Mapped[Optional["MOT17Evaluation"]] = relationship("MOT17Evaluation", back_populates="tracking_job", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tracking_jobs_video_created", "video_id", "created_at"),
    )
