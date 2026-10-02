"""
Video Management API Presentation Router (Backend API Layer Tier).

Exposes HTTP REST endpoints for uploading video files, listing user-owned video assets,
and retrieving individual video metadata details.

Architectural Role:
- Enforces authentication checks on all video endpoints via `get_current_user`.
- Validates file payloads (`UploadFile`) and delegates disk streaming & metadata extraction to `VideoService`.
- Returns serialized `VideoResponse` DTOs.
"""

from typing import List
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.models.user import User
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.video import VideoResponse
from backend.app.services.video_service import VideoService

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=VideoResponse, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> VideoResponse:
    """
    Upload a raw video file asset, extract OpenCV metadata, and persist record in database.

    Args:
        file: Multipart file stream uploaded by the client (.mp4, .avi, .mov, .mkv).
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        VideoResponse schema populated with extracted FPS, duration, dimensions, and file path.

    Raises:
        HTTPException 422 Unprocessable Entity: If file extension is unsupported.
        HTTPException 413 Request Entity Too Large: If file size exceeds 500 MB.
    """
    video_repo = VideoRepository(session)
    service = VideoService(video_repo)
    return await service.upload_video(file, current_user.id)


@router.get("", response_model=List[VideoResponse])
async def list_videos(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[VideoResponse]:
    """
    Retrieve a paginated list of uploaded video assets owned by the current user.

    Args:
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        List of VideoResponse schemas ordered by creation date descending.
    """
    video_repo = VideoRepository(session)
    service = VideoService(video_repo)
    return await service.list_user_videos(current_user.id)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> VideoResponse:
    """
    Fetch metadata details for a specific video asset by unique UUID.

    Args:
        video_id: Target video UUID path parameter.
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        VideoResponse schema for target video.

    Raises:
        HTTPException 404 Not Found: If video asset does not exist or belong to current user.
    """
    video_repo = VideoRepository(session)
    service = VideoService(video_repo)
    return await service.get_video(video_id, current_user.id)
