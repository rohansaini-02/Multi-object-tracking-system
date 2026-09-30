"""
TrackingJob Repository for Database CRUD Operations.
"""

from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tracking_job import TrackingJob, JobStatus


class TrackingJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, job_id: str) -> Optional[TrackingJob]:
        return await self.session.get(TrackingJob, job_id)

    async def create(
        self,
        video_id: str,
        user_id: str,
        config: Optional[dict] = None,
    ) -> TrackingJob:
        job = TrackingJob(
            video_id=video_id,
            user_id=user_id,
            status=JobStatus.QUEUED,
            progress=0,
            config=config if config is not None else {},
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_latest_by_video(self, video_id: str) -> Optional[TrackingJob]:
        stmt = (
            select(TrackingJob)
            .where(TrackingJob.video_id == video_id)
            .order_by(TrackingJob.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        values = {"status": status}
        if progress is not None:
            values["progress"] = progress
        if error_message is not None:
            values["error_message"] = error_message

        stmt = (
            update(TrackingJob)
            .where(TrackingJob.id == job_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def list_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[TrackingJob]:
        stmt = (
            select(TrackingJob)
            .where(TrackingJob.user_id == user_id)
            .order_by(TrackingJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
