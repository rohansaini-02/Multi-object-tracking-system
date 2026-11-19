"""
Tracking Job Management API Presentation Router.
"""

import os
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.core.file_response import stream_file_response
from backend.app.models.user import User
from backend.app.repositories.tracking_job_repository import TrackingJobRepository
from backend.app.repositories.track_result_repository import TrackResultRepository
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.tracking_job import JobCreateRequest, JobResponse, JobResultsResponse
from backend.app.services.job_artifact_service import parse_mot_frames
from backend.app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _build_service(session: AsyncSession) -> JobService:
    """Instantiate the JobService with all required repositories."""
    return JobService(
        TrackingJobRepository(session),
        VideoRepository(session),
        TrackResultRepository(session),
    )


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    req: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    service = _build_service(session)
    return await service.create_and_dispatch_job(req, current_user.id)


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[JobResponse]:
    service = _build_service(session)
    return await service.list_user_jobs(current_user.id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    service = _build_service(session)
    return await service.get_job(job_id, current_user.id)


@router.get("/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobResultsResponse:
    """
    Fetch parsed tracking statistics for a tracking job.

    Args:
        job_id: Target tracking job UUID path parameter.
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        JobResultsResponse schema with track counts, frame statistics and artifact availability.

    Raises:
        HTTPException 404 Not Found: If the job does not exist or belong to current user.
    """
    service = _build_service(session)
    return await service.get_job_results(job_id, current_user.id)


@router.get("/{job_id}/download/video")
async def download_annotated_video(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """
    Download the annotated (tracked) MP4 video artifact produced for a tracking job.

    Args:
        job_id: Target tracking job UUID path parameter.
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        StreamingResponse streaming the annotated MP4 file.

    Raises:
        HTTPException 404 Not Found: If the job does not exist or the artifact is missing.
    """
    service = _build_service(session)
    artifacts = await service.get_job_artifacts(job_id, current_user.id)

    video_paths = artifacts["paths"]
    path = video_paths["annotated_video_path"]
    if not path or not os.path.isfile(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated video is not available for this job yet.",
        )

    return stream_file_response(
        path,
        media_type="video/mp4",
        filename=f"{job_id}_annotated.mp4",
    )


@router.get("/{job_id}/download/mot")
async def download_tracking_data(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """
    Download the MOT challenge formatted tracking results text file for a tracking job.

    Args:
        job_id: Target tracking job UUID path parameter.
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        StreamingResponse streaming the MOT results text file.

    Raises:
        HTTPException 404 Not Found: If the job does not exist or the artifact is missing.
    """
    service = _build_service(session)
    artifacts = await service.get_job_artifacts(job_id, current_user.id)

    mot_paths = artifacts["paths"]
    path = mot_paths["output_mot_path"]
    if not path or not os.path.isfile(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MOT tracking results are not available for this job yet.",
        )

    return stream_file_response(
        path,
        media_type="text/plain",
        filename=f"{job_id}_mot.txt",
    )


@router.get("/{job_id}/frames")
async def get_job_frame_data(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Return per-frame bounding box tracking data for frontend canvas overlay rendering.

    The response contains a frame-indexed dictionary where each key is a frame number
    and the value is a list of detection objects with coordinates and confidence scores.
    This allows the frontend to draw real-time overlays on the source video.

    Args:
        job_id: Target tracking job UUID path parameter.
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        JSON with 'frames' (frame-indexed bbox data), 'total_frames', and 'fps' fields.
        'fps' is the frame rate of the *source video* so the client can map the
        video timeline onto the frame indices.
    """
    service = _build_service(session)
    artifacts = await service.get_job_artifacts(job_id, current_user.id)

    mot_paths = artifacts["paths"]
    frames = parse_mot_frames(mot_paths["output_mot_path"])
    fps = await service.get_source_video_fps(job_id, current_user.id) or 30.0

    return {
        "frames": {str(key): value for key, value in frames.items()},
        "total_frames": max(frames.keys()) if frames else 0,
        "fps": fps,
    }


@router.get("/{job_id}/source-video")
async def stream_source_video(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """
    Stream the original (un-annotated) source video for a tracking job so the frontend
    can play it under a canvas overlay with controllable annotation layers.

    Args:
        job_id: Target tracking job UUID path parameter.
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        StreamingResponse streaming the original video file.

    Raises:
        HTTPException 404 Not Found: If the job or source video does not exist.
    """
    service = _build_service(session)
    job = await service.get_job(job_id, current_user.id)

    video_repo = VideoRepository(session)
    video = await video_repo.get_by_id(job.video_id)
    if not video or not video.file_path or not os.path.isfile(video.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original source video is not available on disk.",
        )

    return stream_file_response(
        video.file_path,
        media_type="video/mp4",
        filename=f"{job_id}_source.mp4",
    )


@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Delete a tracking job, its persisted results, and disk output artifacts.

    Args:
        job_id: UUID of tracking job to delete.
        current_user: Authenticated User entity resolved from JWT bearer token.
        session: Injected async database session context.

    Returns:
        Confirmation dictionary with deleted job ID.
    """
    service = _build_service(session)
    return await service.delete_job(job_id, current_user.id)
