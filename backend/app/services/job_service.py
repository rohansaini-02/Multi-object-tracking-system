"""
Job Service orchestrating TrackingJob creation and ML pipeline dispatch.
"""

import asyncio
import os
from typing import List, Optional
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.models.tracking_job import JobStatus, TrackingJob
from backend.app.repositories.tracking_job_repository import TrackingJobRepository
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.tracking_job import JobCreateRequest, JobResponse
from ml.pipeline import TrackingPipeline


def _run_tracking_job_sync(
    video_path: str,
    output_video_path: str,
    output_mot_path: str,
    conf_threshold: float,
    max_cosine_distance: float,
    max_age: int,
    n_init: int,
) -> dict:
    """Synchronous pipeline execution worker for background thread."""
    pipeline = TrackingPipeline(
        conf_threshold=conf_threshold,
    )
    # Configure custom parameters on tracker if needed
    pipeline.tracker.max_cosine_distance = max_cosine_distance
    pipeline.tracker.max_age = max_age
    pipeline.tracker.n_init = n_init

    res = pipeline.run(
        input_video_path=video_path,
        output_video_path=output_video_path,
        output_mot_path=output_mot_path,
    )
    return {
        "total_frames": res.total_frames,
        "processed_frames": res.processed_frames,
        "total_tracks": res.total_tracks,
        "fps": res.fps,
        "output_video_path": res.output_video_path,
        "output_mot_path": res.output_mot_path,
    }


class JobService:
    def __init__(self, job_repo: TrackingJobRepository, video_repo: VideoRepository):
        self.job_repo = job_repo
        self.video_repo = video_repo

    async def create_and_dispatch_job(self, req: JobCreateRequest, user_id: str) -> JobResponse:
        video = await self.video_repo.get_by_id(req.video_id)
        if not video or video.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video asset '{req.video_id}' not found.",
            )

        config = {
            "conf_threshold": req.conf_threshold,
            "max_cosine_distance": req.max_cosine_distance,
            "max_age": req.max_age,
            "n_init": req.n_init,
        }

        job = await self.job_repo.create(
            video_id=req.video_id,
            user_id=user_id,
            config=config,
        )

        # Dispatch background pipeline processing task asynchronously
        asyncio.create_task(
            self._execute_pipeline(job.id, video.file_path, config)
        )

        return JobResponse.model_validate(job)

    async def _execute_pipeline(self, job_id: str, video_path: str, config: dict):
        try:
            await self.job_repo.update_status(job_id, JobStatus.PROCESSING, progress=10)

            output_dir = os.path.join(settings.UPLOAD_DIR, "outputs")
            os.makedirs(output_dir, exist_ok=True)

            out_video_path = os.path.join(output_dir, f"{job_id}_annotated.mp4")
            out_mot_path = os.path.join(output_dir, f"{job_id}_mot.txt")

            res = await asyncio.to_thread(
                _run_tracking_job_sync,
                video_path,
                out_video_path,
                out_mot_path,
                config.get("conf_threshold", 0.50),
                config.get("max_cosine_distance", 0.20),
                config.get("max_age", 30),
                config.get("n_init", 3),
            )

            await self.job_repo.update_status(
                job_id, JobStatus.COMPLETED, progress=100
            )
        except Exception as e:
            await self.job_repo.update_status(
                job_id, JobStatus.FAILED, progress=0, error_message=str(e)
            )

    async def get_job(self, job_id: str, user_id: str) -> JobResponse:
        job = await self.job_repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )
        return JobResponse.model_validate(job)

    async def list_user_jobs(self, user_id: str) -> List[JobResponse]:
        jobs = await self.job_repo.list_by_user(user_id)
        return [JobResponse.model_validate(j) for j in jobs]
