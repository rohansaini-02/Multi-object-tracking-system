"""
Tracking Job Management API Presentation Router.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.models.user import User
from backend.app.repositories.tracking_job_repository import TrackingJobRepository
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.tracking_job import JobCreateRequest, JobResponse
from backend.app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    req: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    job_repo = TrackingJobRepository(session)
    video_repo = VideoRepository(session)
    service = JobService(job_repo, video_repo)
    return await service.create_and_dispatch_job(req, current_user.id)


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[JobResponse]:
    job_repo = TrackingJobRepository(session)
    video_repo = VideoRepository(session)
    service = JobService(job_repo, video_repo)
    return await service.list_user_jobs(current_user.id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    job_repo = TrackingJobRepository(session)
    video_repo = VideoRepository(session)
    service = JobService(job_repo, video_repo)
    return await service.get_job(job_id, current_user.id)
