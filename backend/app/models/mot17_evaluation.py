"""
SQLAlchemy ORM Model for MOT17Evaluations table.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base

if TYPE_CHECKING:
    from backend.app.models.tracking_job import TrackingJob


class MOT17Evaluation(Base):
    __tablename__ = "mot17_evaluations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracking_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    sequence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mota: Mapped[float] = mapped_column(Float, nullable=False)
    idf1: Mapped[float] = mapped_column(Float, nullable=False)
    num_switches: Mapped[int] = mapped_column(Integer, nullable=False)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    mostly_tracked: Mapped[int] = mapped_column(Integer, nullable=False)
    mostly_lost: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    tracking_job: Mapped["TrackingJob"] = relationship("TrackingJob", back_populates="mot17_evaluation")
