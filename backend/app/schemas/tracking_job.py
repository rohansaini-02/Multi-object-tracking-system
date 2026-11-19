"""
Tracking Job Pydantic Schemas for Request & Response DTO Serialization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class JobCreateRequest(BaseModel):
    video_id: str
    conf_threshold: float = 0.25
    max_cosine_distance: float = 0.20
    max_age: int = 30
    n_init: int = 1


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    user_id: str
    status: str
    progress: int
    config: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TrackDetail(BaseModel):
    """
    Per-identity tracking statistics extracted from the MOT challenge results file.

    Attributes:
        track_id: Stable identity identifier assigned by the tracker.
        frames: Number of frames the identity was detected in.
        avg_confidence: Mean detection confidence across all of its detections.
        first_frame: First frame index the identity appears in.
        last_frame: Last frame index the identity appears in.
    """

    track_id: int
    frames: int
    avg_confidence: float
    first_frame: int
    last_frame: int


class JobResultsResponse(BaseModel):
    """
    Aggregated tracking statistics for a completed (or in-flight) tracking job.

    Attributes:
        job_id: Identifier of the tracking job the statistics belong to.
        status: Current lifecycle status of the job (QUEUED/PROCESSING/COMPLETED/FAILED).
        video_id: Identifier of the source video asset tracked by the job.
        total_tracks: Number of unique object identities detected across the clip.
        total_detections: Total number of per-frame detection rows for all tracks.
        total_frames: Number of distinct video frames covered by the tracking output.
        fps: Processing throughput measured by the pipeline (frames per second).
        avg_track_length: Mean number of frames an identity remained visible.
        longest_track_frames: Frame count of the single longest tracked identity.
        tracks: Per-identity statistics for the most active tracked objects.
        annotated_video_available: Flag indicating the annotated MP4 artifact exists on disk.
        mot_results_available: Flag indicating the MOT challenge text artifact exists on disk.
        annotated_video_url: Static URL of the annotated MP4 artifact.
        mot_results_url: Static URL of the MOT challenge text artifact.
        error_message: Failure detail string if the job terminated with an error.
    """

    job_id: str
    status: str
    video_id: str
    total_tracks: int = 0
    total_detections: int = 0
    total_frames: int = 0
    fps: float = 0.0
    avg_track_length: float = 0.0
    longest_track_frames: int = 0
    tracks: List[TrackDetail] = []
    annotated_video_available: bool = False
    mot_results_available: bool = False
    source_video_url: Optional[str] = None
    annotated_video_url: Optional[str] = None
    mot_results_url: Optional[str] = None
    error_message: Optional[str] = None
