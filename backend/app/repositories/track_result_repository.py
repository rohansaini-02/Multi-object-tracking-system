"""
TrackResult Repository for Database CRUD Operations.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.track_result import TrackResult


class TrackResultRepository:
    """Data access repository managing database operations for TrackResult records."""

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: Active request-scoped AsyncSession instance.
        """
        self.session = session

    async def get_by_job_id(self, job_id: str) -> Optional[TrackResult]:
        """
        Query the TrackResult record attached to a tracking job.

        Args:
            job_id: Unique tracking job identifier string.

        Returns:
            TrackResult entity instance or None if not found.
        """
        stmt = select(TrackResult).where(TrackResult.job_id == job_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(
        self,
        job_id: str,
        total_tracks: int,
        fps: float,
        output_video_path: Optional[str] = None,
        output_mot_path: Optional[str] = None,
        summary: Optional[dict] = None,
    ) -> TrackResult:
        """
        Insert or refresh the single track result row attached to a tracking job.

        Args:
            job_id: Unique tracking job identifier string.
            total_tracks: Number of unique identities detected by the tracker.
            fps: Pipeline processing throughput in frames per second.
            output_video_path: Disk path of the annotated MP4 artifact.
            output_mot_path: Disk path of the MOT challenge text artifact.
            summary: Optional JSON blob with aggregate tracking statistics.

        Returns:
            The persisted (and refreshed) TrackResult ORM instance.
        """
        record = await self.get_by_job_id(job_id)
        if record is None:
            record = TrackResult(job_id=job_id)
            self.session.add(record)

        record.total_tracks = total_tracks
        record.fps = fps
        record.output_video_path = output_video_path
        record.output_mot_path = output_mot_path
        record.summary_json = summary if summary is not None else {}

        await self.session.commit()
        await self.session.refresh(record)
        return record
