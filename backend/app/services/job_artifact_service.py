"""
Job Artifact Resolution & Tracking Result Parsing Service (Backend Application Business Logic Tier).

Locates the pipeline output artifacts (annotated video + MOT challenge text file) that
the background DeepSORT worker writes to disk for a given tracking job, and parses the
MOT text file into aggregate tracking statistics consumed by the frontend viewer.

Architectural Role:
- Centralizes the on-disk artifact naming convention (`{job_id}_annotated.mp4` /
  `{job_id}_mot.txt`) between the job dispatch worker and the artifact serving API.
- Performs lightweight, dependency-free parsing of MOT challenge rows so that track
  counts can be reported without loading any heavy computer-vision stack.
"""

import os
from typing import Dict, List, Optional

from backend.app.core.config import settings

# Sub-folder of the upload directory where the tracking pipeline writes its artifacts.
ARTIFACT_SUBDIR = "outputs"

# Public URL prefix the upload directory is mounted under by the FastAPI application.
STATIC_URL_PREFIX = "/uploads"


def get_output_dir() -> str:
    """
    Return the absolute directory path where tracking pipeline artifacts are stored.

    Returns:
        Directory path string ending with the 'outputs' sub-folder.
    """
    return os.path.join(settings.UPLOAD_DIR, ARTIFACT_SUBDIR)


def build_artifact_paths(job_id: str) -> Dict[str, str]:
    """
    Build the deterministic on-disk artifact paths for a tracking job.

    Args:
        job_id: Unique tracking job identifier string.

    Returns:
        Dictionary with 'annotated_video_path' and 'output_mot_path' paths.
    """
    output_dir = get_output_dir()
    return {
        "annotated_video_path": os.path.join(output_dir, f"{job_id}_annotated.mp4"),
        "output_mot_path": os.path.join(output_dir, f"{job_id}_mot.txt"),
    }


def build_artifact_temp_paths(job_id: str) -> Dict[str, str]:
    """
    Build the staging paths a tracking job writes to while it is still running.

    The pipeline writes to these paths first and the finished artifacts are then
    moved into their final location with `os.replace`, which is atomic on the
    same volume. The public artifact URLs therefore never point at a partially
    written file - serving one through the static mount would advertise a
    stale Content-Length and abort the response mid-stream.

    Args:
        job_id: Unique tracking job identifier string.

    Returns:
        Dictionary with 'annotated_video_path' and 'output_mot_path' staging paths.
    """
    output_dir = get_output_dir()
    return {
        "annotated_video_path": os.path.join(output_dir, f"{job_id}_annotated.part.mp4"),
        "output_mot_path": os.path.join(output_dir, f"{job_id}_mot.part.txt"),
    }


def build_artifact_urls(job_id: str) -> Dict[str, str]:
    """
    Build the static (public) URLs for the job artifacts served by the backend.

    Args:
        job_id: Unique tracking job identifier string.

    Returns:
        Dictionary with 'annotated_video_url' and 'mot_results_url' URL strings.
    """
    return {
        "annotated_video_url": f"{STATIC_URL_PREFIX}/{ARTIFACT_SUBDIR}/{job_id}_annotated.mp4",
        "mot_results_url": f"{STATIC_URL_PREFIX}/{ARTIFACT_SUBDIR}/{job_id}_mot.txt",
    }


def artifact_exists(path: str) -> bool:
    """
    Check whether an artifact file is present on disk.

    Args:
        path: Absolute or relative file system path.

    Returns:
        True if the path points to an existing regular file, False otherwise.
    """
    return bool(path) and os.path.isfile(path)


def parse_mot_frames(mot_path: str) -> Dict[int, List[Dict]]:
    """
    Parse a MOT challenge formatted text file into a frame-indexed lookup of
    bounding box entries for real-time canvas overlay rendering.

    Each entry contains the raw coordinates needed to draw bounding boxes, ID
    labels, confidence scores, and motion paths on the frontend.

    Expected row format (standard MOT Challenge):
        frame_id, track_id, left, top, width, height, conf, -1, -1, -1

    Args:
        mot_path: File system path of the MOT challenge results text file.

    Returns:
        Dictionary mapping frame index (int) to a list of detection dicts,
        each containing: track_id, x1, y1, x2, y2, w, h, confidence.
        Returns an empty dictionary when the file does not exist or is empty.
    """
    frames: Dict[int, List[Dict]] = {}

    if not mot_path or not os.path.isfile(mot_path):
        return frames

    try:
        with open(mot_path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(",")
                if len(parts) < 7:
                    continue

                try:
                    frame = int(float(parts[0]))
                    track_id = int(float(parts[1]))
                    # Standard MOT Challenge format: parts[2] is left (x), parts[3] is top (y)
                    left = float(parts[2])
                    top = float(parts[3])
                    width = float(parts[4])
                    height = float(parts[5])
                    confidence = float(parts[6])
                except ValueError:
                    continue

                entry = {
                    "track_id": track_id,
                    "x1": round(left, 2),
                    "y1": round(top, 2),
                    "x2": round(left + width, 2),
                    "y2": round(top + height, 2),
                    "w": round(width, 2),
                    "h": round(height, 2),
                    "confidence": round(confidence, 4),
                }
                frames.setdefault(frame, []).append(entry)
    except OSError:
        return frames

    return frames


def parse_mot_results(mot_path: str, max_tracks: int = 10) -> Dict:
    """
    Parse a MOT challenge formatted text file into aggregate tracking statistics.

    Args:
        mot_path: File system path of the MOT challenge results text file.
        max_tracks: Maximum number of per-track entries returned (longest first).

    Returns:
        Dictionary containing total_tracks, total_detections, total_frames,
        first_frame, last_frame, avg_track_length, longest_track_frames and a
        'tracks' list describing the most active identities.
        Returns a zeroed dictionary when the file does not exist.
    """
    empty_stats: Dict = {
        "total_tracks": 0,
        "total_detections": 0,
        "total_frames": 0,
        "first_frame": 0,
        "last_frame": 0,
        "avg_track_length": 0.0,
        "longest_track_frames": 0,
        "tracks": [],
    }

    if not mot_path or not os.path.isfile(mot_path):
        return empty_stats

    track_frames: Dict[int, int] = {}
    track_conf_sum: Dict[int, float] = {}
    track_first_frame: Dict[int, int] = {}
    track_last_frame: Dict[int, int] = {}

    total_detections = 0
    first_frame = 0
    last_frame = 0

    try:
        with open(mot_path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(",")
                if len(parts) < 7:
                    continue

                try:
                    frame = int(float(parts[0]))
                    track_id = int(float(parts[1]))
                    confidence = float(parts[6])
                except ValueError:
                    continue

                total_detections += 1
                track_frames[track_id] = track_frames.get(track_id, 0) + 1
                track_conf_sum[track_id] = track_conf_sum.get(track_id, 0.0) + confidence

                if track_id not in track_first_frame or frame < track_first_frame[track_id]:
                    track_first_frame[track_id] = frame
                if track_id not in track_last_frame or frame > track_last_frame[track_id]:
                    track_last_frame[track_id] = frame

                if first_frame == 0 or frame < first_frame:
                    first_frame = frame
                if frame > last_frame:
                    last_frame = frame
    except OSError:
        return empty_stats

    total_tracks = len(track_frames)
    ordered_tracks = sorted(track_frames.items(), key=lambda item: item[1], reverse=True)

    avg_track_length = (
        sum(track_frames.values()) / total_tracks if total_tracks else 0.0
    )
    longest_track_frames = ordered_tracks[0][1] if ordered_tracks else 0

    tracks: List[Dict] = []
    for track_id, frames in ordered_tracks[:max_tracks]:
        tracks.append(
            {
                "track_id": track_id,
                "frames": frames,
                "avg_confidence": round(track_conf_sum.get(track_id, 0.0) / frames, 4),
                "first_frame": track_first_frame.get(track_id, 0),
                "last_frame": track_last_frame.get(track_id, 0),
            }
        )

    return {
        "total_tracks": total_tracks,
        "total_detections": total_detections,
        "total_frames": (last_frame - first_frame + 1) if last_frame else 0,
        "first_frame": first_frame,
        "last_frame": last_frame,
        "avg_track_length": round(avg_track_length, 2),
        "longest_track_frames": longest_track_frames,
        "tracks": tracks,
    }
