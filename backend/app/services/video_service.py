"""
Video Asset Service (Backend Application Business Logic Tier).

Coordinates video upload validation, binary file streaming to disk storage,
and non-blocking OpenCV metadata extraction off the main asyncio event loop thread.

Architectural Role:
- Enforces file format constraints (.mp4, .avi, .mov, .mkv) and 500MB size limit.
- Executes synchronous `cv2.VideoCapture` calls off-thread via `asyncio.to_thread` to maintain sub-300ms API response SLAs.
- Interacts with `VideoRepository` for data persistence.
"""

import asyncio
import os
import uuid
from typing import List, Optional, Tuple
import cv2
from fastapi import HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.models.video import Video
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.video import VideoResponse

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB limit


def _extract_metadata_sync(dest_path: str) -> Tuple[Optional[float], Optional[int], Optional[int], Optional[int], Optional[float]]:
    """
    Synchronous worker function to extract OpenCV video metadata off the main event loop thread.

    Args:
        dest_path: Absolute disk file path to uploaded video file.

    Returns:
        Tuple containing (fps, width, height, frame_count, duration) or Nones on error.
    """
    fps, width, height, frame_count, duration = None, None, None, None, None
    try:
        cap = cv2.VideoCapture(dest_path)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fps > 0 and frame_count > 0:
                duration = frame_count / fps
            cap.release()
    except Exception:
        pass
    return fps, width, height, frame_count, duration


class VideoService:
    """
    Service orchestrating video asset upload, storage, and metadata indexing.
    """

    def __init__(self, video_repo: VideoRepository):
        """
        Args:
            video_repo: Injected VideoRepository instance for database persistence operations.
        """
        self.video_repo = video_repo

    async def upload_video(self, file: UploadFile, user_id: str) -> VideoResponse:
        """
        Stream uploaded file to disk, extract metadata asynchronously, and create Video database record.

        Args:
            file: Multipart UploadFile instance from client request.
            user_id: UUID string of the uploading user.

        Returns:
            VideoResponse DTO representing the newly created video record.

        Raises:
            HTTPException 422: If file extension is not in ALLOWED_EXTENSIONS.
            HTTPException 413: If file total byte size exceeds MAX_FILE_SIZE (500MB).
            HTTPException 500: If disk write operation fails.
        """
        filename = file.filename or "video.mp4"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        dest_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        # Write uploaded file stream to disk in 1MB chunks
        file_size = 0
        try:
            with open(dest_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    file_size += len(chunk)
                    if file_size > MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="File exceeds maximum allowed size of 500MB.",
                        )
                    buffer.write(chunk)
        except Exception as e:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write video file to disk: {str(e)}",
            )

        # Non-blocking OpenCV metadata extraction off the main asyncio thread
        fps, width, height, frame_count, duration = await asyncio.to_thread(
            _extract_metadata_sync, dest_path
        )

        video = await self.video_repo.create(
            user_id=user_id,
            filename=filename,
            file_path=dest_path,
            file_size=file_size,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            frame_count=frame_count,
        )

        return VideoResponse.model_validate(video)

    async def get_video(self, video_id: str, user_id: str) -> VideoResponse:
        """
        Fetch Video entity by ID and verify user ownership.

        Args:
            video_id: UUID string of target video.
            user_id: UUID string of requesting user.

        Returns:
            VideoResponse DTO for the target video.

        Raises:
            HTTPException 404: If video is not found or does not belong to user.
        """
        video = await self.video_repo.get_by_id(video_id)
        if not video or video.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{video_id}' not found.",
            )
        return VideoResponse.model_validate(video)

    async def list_user_videos(self, user_id: str) -> List[VideoResponse]:
        """
        Retrieve all video assets uploaded by a specific user.

        Args:
            user_id: Target user UUID string.

        Returns:
            List of VideoResponse DTOs.
        """
        videos = await self.video_repo.list_by_user(user_id)
        return [VideoResponse.model_validate(v) for v in videos]
