"""
Video API Pydantic Schemas (FastAPI Data Transfer Objects).

Provides serialization and request/response validation contracts for video metadata.
Separates internal SQLAlchemy ORM entities from external HTTP API interfaces.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VideoResponse(BaseModel):
    """
    Data Transfer Object (DTO) for video metadata responses.

    Serializes stored video attributes into JSON for client consumption.
    Enables ORM mode for seamless conversion from SQLAlchemy Video instances.

    Attributes:
        id: Unique UUID string identifying the video.
        filename: Original user-provided filename of the video asset.
        file_size: Total disk size of the uploaded file in bytes.
        duration: Video clip duration in seconds (extracted via OpenCV).
        fps: Frame rate of the video sequence in frames per second.
        width: Frame width dimension in pixels.
        height: Frame height dimension in pixels.
        frame_count: Total frame count in the video sequence.
        created_at: ISO-8601 UTC timestamp of video upload.
    """

    id: str = Field(..., description="Unique UUID identifier for the video asset.")
    filename: str = Field(..., description="Original name of the uploaded video file.")
    file_size: int = Field(..., description="File size on disk in bytes.")
    duration: Optional[float] = Field(None, description="Video duration in seconds.")
    fps: Optional[float] = Field(None, description="Video frame rate (FPS).")
    width: Optional[int] = Field(None, description="Video frame width in pixels.")
    height: Optional[int] = Field(None, description="Video frame height in pixels.")
    frame_count: Optional[int] = Field(None, description="Total number of frames in the video.")
    created_at: datetime = Field(..., description="UTC timestamp when video was uploaded.")

    model_config = ConfigDict(from_attributes=True)
