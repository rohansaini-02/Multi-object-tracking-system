"""
SQLAlchemy ORM Model for TrackResults table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base

if TYPE_CHECKING:
    from backend.app.models.tracking_job import TrackingJob


class TrackResult(Base):
    __tablename__ = "track_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracking_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    total_tracks: Mapped[int] = mapped_column(Integer, nullable=False)
    fps: Mapped[float] = mapped_column(Float, nullable=False)
    output_video_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    output_mot_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    tracking_job: Mapped["TrackingJob"] = relationship("TrackingJob", back_populates="track_result")
