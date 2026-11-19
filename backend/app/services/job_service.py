"""
Job Service orchestrating TrackingJob creation and ML pipeline dispatch.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status

from backend.app.db import database
from backend.app.models.tracking_job import JobStatus
from backend.app.repositories.tracking_job_repository import TrackingJobRepository
from backend.app.repositories.track_result_repository import TrackResultRepository
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.tracking_job import (
    JobCreateRequest,
    JobResponse,
    JobResultsResponse,
)
from backend.app.services.job_artifact_service import (
    artifact_exists,
    build_artifact_paths,
    build_artifact_temp_paths,
    build_artifact_urls,
    get_output_dir,
    parse_mot_results,
)

logger = logging.getLogger("uvicorn.error")

# Strong references to in-flight background tasks so they are not garbage collected.
_BACKGROUND_TASKS: set = set()

# Repository root. The tracking worker is launched from this directory so that
# relative weight paths (`weights/yolov8m.pt`) resolve exactly like they do for
# the rest of the project.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Upper bound for a single tracking run. A long 1080p clip on CPU inference can
# legitimately take tens of minutes, so this limit only exists to reclaim a
# worker that has hung instead of leaving it running forever.
WORKER_TIMEOUT_SECONDS = 60 * 60 * 3


def _read_worker_result(result_path: str) -> Dict[str, Any]:
    """
    Read the JSON result document produced by the tracking worker.

    Args:
        result_path: Filesystem path of the worker result document.

    Returns:
        The decoded document, or an empty dictionary when it cannot be read.
    """
    try:
        with open(result_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _discard_partial_artifacts(*paths: str) -> None:
    """Delete staging files left behind by a failed tracking run."""
    for path in paths:
        try:
            if path and os.path.isfile(path):
                os.remove(path)
        except OSError:
            logger.warning("[JOB WARNING] Could not remove partial artifact '%s'.", path)


async def _run_tracking_job_in_worker(
    video_path: str,
    output_video_path: str,
    output_mot_path: str,
    conf_threshold: float,
    max_cosine_distance: float,
    max_age: int,
    n_init: int,
    progress_callback: Optional[Callable[[int, int, int], Any]] = None,
) -> Dict[str, Any]:
    """
    Execute the tracking pipeline inside a dedicated worker process.

    Uses a thread-backed synchronous subprocess invocation so that it is fully
    compatible with any asyncio event loop on Windows (including SelectorEventLoop,
    which does not implement asyncio.create_subprocess_exec and raises NotImplementedError).
    """
    loop = asyncio.get_running_loop()

    def _worker_runner() -> Dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="mot_worker_") as tmp_dir:
            result_path = os.path.join(tmp_dir, "worker_result.json")
            payload = {
                "video_path": video_path,
                "output_video_path": output_video_path,
                "output_mot_path": output_mot_path,
                "result_path": result_path,
                "conf_threshold": conf_threshold,
                "max_cosine_distance": max_cosine_distance,
                "max_age": max_age,
                "n_init": n_init,
            }

            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = os.pathsep.join(
                [str(REPO_ROOT)] + ([existing_pythonpath] if existing_pythonpath else [])
            )

            process = subprocess.Popen(
                [sys.executable, "-m", "backend.app.workers.tracking_worker"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(REPO_ROOT),
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            # Send payload via stdin and close
            if process.stdin:
                process.stdin.write(json.dumps(payload))
                process.stdin.close()

            stderr_lines = []
            if process.stderr:
                for line in iter(process.stderr.readline, ""):
                    stderr_lines.append(line)
                    stripped = line.strip()
                    if stripped.startswith("PROGRESS:") and progress_callback is not None:
                        parts = stripped.split(":")
                        if len(parts) >= 4:
                            try:
                                curr_f = int(parts[1])
                                tot_f = int(parts[2])
                                pct = int(parts[3])
                                asyncio.run_coroutine_threadsafe(
                                    progress_callback(curr_f, tot_f, pct), loop
                                )
                            except Exception:
                                pass

            process.wait(timeout=WORKER_TIMEOUT_SECONDS)
            worker_log = "".join(stderr_lines).strip()
            if worker_log:
                logger.debug("[WORKER] %s", worker_log[-2000:])

            result = _read_worker_result(result_path)

            if process.returncode != 0:
                detail = result.get("error") or worker_log[-2000:] or "no details reported"
                raise RuntimeError(
                    f"Tracking worker exited with code {process.returncode}: {detail}"
                )

            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "Tracking worker reported an unknown failure.")

            return result

    return await asyncio.to_thread(_worker_runner)


async def recover_orphaned_jobs() -> int:
    """
    Fail every job that was still in flight when the server was stopped.

    Tracking jobs run in a worker process that does not survive an API restart,
    so a job left in QUEUED or PROCESSING can never complete on its own. Marking
    them as FAILED keeps the operator UI honest instead of showing a progress
    bar that never moves.

    Returns:
        Number of jobs that were transitioned to FAILED.
    """
    async with database.AsyncSessionLocal() as session:
        repo = TrackingJobRepository(session)
        orphaned = await repo.list_by_status(JobStatus.QUEUED)
        orphaned += await repo.list_by_status(JobStatus.PROCESSING)

        for job in orphaned:
            await repo.update_status(
                job.id,
                JobStatus.FAILED,
                progress=0,
                error_message="Server restarted while this job was running.",
            )

        return len(orphaned)


class JobService:
    def __init__(
        self,
        job_repo: TrackingJobRepository,
        video_repo: VideoRepository,
        track_result_repo: Optional[TrackResultRepository] = None,
    ):
        self.job_repo = job_repo
        self.video_repo = video_repo
        self.track_result_repo = track_result_repo

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
        task = asyncio.create_task(
            self._execute_pipeline(job.id, video.file_path, config)
        )
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)

        return JobResponse.model_validate(job)

    async def _execute_pipeline(self, job_id: str, video_path: str, config: dict):
        """Run the tracking pipeline and persist the resulting artifacts + statistics."""
        artifact_paths = build_artifact_paths(job_id)
        staging_paths = build_artifact_temp_paths(job_id)

        final_video = artifact_paths["annotated_video_path"]
        final_mot = artifact_paths["output_mot_path"]
        staging_video = staging_paths["annotated_video_path"]
        staging_mot = staging_paths["output_mot_path"]

        try:
            await self._update_job_status(job_id, JobStatus.PROCESSING, progress=5)

            output_dir = get_output_dir()
            os.makedirs(output_dir, exist_ok=True)

            last_saved_pct = 5

            async def on_progress(curr_f: int, tot_f: int, pct: int):
                nonlocal last_saved_pct
                if pct >= last_saved_pct + 2 or pct == 95:
                    last_saved_pct = pct
                    try:
                        await self._update_job_status(
                            job_id, JobStatus.PROCESSING, progress=pct
                        )
                    except Exception as prog_exc:
                        logger.debug("Failed to record intermediate progress: %s", prog_exc)

            res = await _run_tracking_job_in_worker(
                video_path,
                staging_video,
                staging_mot,
                config.get("conf_threshold", 0.50),
                config.get("max_cosine_distance", 0.20),
                config.get("max_age", 30),
                config.get("n_init", 3),
                progress_callback=on_progress,
            )

            mot_stats = parse_mot_results(staging_mot)
            summary_stats = {
                "total_tracks": mot_stats["total_tracks"],
                "total_detections": mot_stats["total_detections"],
                "total_frames": mot_stats["total_frames"],
                "first_frame": mot_stats["first_frame"],
                "last_frame": mot_stats["last_frame"],
                "avg_track_length": mot_stats["avg_track_length"],
                "longest_track_frames": mot_stats["longest_track_frames"],
                "tracks": mot_stats["tracks"],
            }

            # Publish the artifacts atomically. The static mount serves these
            # paths directly, so moving them into place only once they are
            # complete prevents a truncated response with a stale
            # Content-Length header.
            os.replace(staging_video, final_video)
            os.replace(staging_mot, final_mot)

            try:
                await self._persist_track_result(
                    job_id=job_id,
                    total_tracks=int(res.get("total_tracks") or mot_stats["total_tracks"]),
                    fps=float(res.get("fps") or 0.0),
                    output_video_path=final_video,
                    output_mot_path=final_mot,
                    summary=summary_stats,
                )
            except Exception as persist_exc:
                logger.warning(
                    "[JOB WARNING] Could not persist track result for job %s: %s",
                    job_id,
                    persist_exc,
                )

            await self._update_job_status(job_id, JobStatus.COMPLETED, progress=100)
        except Exception as e:
            logger.warning("[JOB ERROR] Job %s failed: %s", job_id, e)
            _discard_partial_artifacts(staging_video, staging_mot)
            err_msg = str(e).strip()
            if not err_msg:
                err_msg = f"{type(e).__name__}: Pipeline execution aborted unexpectedly."
            await self._update_job_status(
                job_id, JobStatus.FAILED, progress=0, error_message=err_msg
            )

    async def _update_job_status(
        self,
        job_id: str,
        job_status: JobStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update job status using a dedicated background session."""
        async with database.AsyncSessionLocal() as session:
            repo = TrackingJobRepository(session)
            await repo.update_status(
                job_id, job_status, progress=progress, error_message=error_message
            )

    async def _persist_track_result(
        self,
        job_id: str,
        total_tracks: int,
        fps: float,
        output_video_path: str,
        output_mot_path: str,
        summary: Dict[str, Any],
    ) -> None:
        """Persist the aggregate tracking statistics for a completed job."""
        async with database.AsyncSessionLocal() as session:
            repo = TrackResultRepository(session)
            await repo.upsert(
                job_id=job_id,
                total_tracks=total_tracks,
                fps=fps,
                output_video_path=output_video_path,
                output_mot_path=output_mot_path,
                summary=summary,
            )

    async def get_job_artifacts(self, job_id: str, user_id: str) -> Dict:
        """
        Resolve the on-disk artifact paths produced by the tracking pipeline.

        Args:
            job_id: Identifier of the tracking job.
            user_id: Identifier of the requesting user (ownership check).

        Returns:
            Dictionary with artifact paths, public URLs and existence flags.

        Raises:
            HTTPException 404: If the job does not exist or belongs to another user.
        """
        job = await self.job_repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )

        paths = build_artifact_paths(job_id)
        urls = build_artifact_urls(job_id)

        return {
            "paths": paths,
            "urls": urls,
            "annotated_video_available": artifact_exists(paths["annotated_video_path"]),
            "mot_results_available": artifact_exists(paths["output_mot_path"]),
        }

    async def get_source_video_fps(self, job_id: str, user_id: str) -> Optional[float]:
        """
        Resolve the true frame rate of the source video behind a tracking job.

        The frame-indexed overlay payload is mapped onto the video timeline by the
        frontend using this value, so it has to be the *video* frame rate. The
        persisted track-result record holds the pipeline processing throughput
        (how many frames per second the tracker managed to process), which is a
        completely different quantity and shifts every overlay box onto the wrong
        frame.

        Args:
            job_id: Identifier of the tracking job.
            user_id: Identifier of the requesting user (ownership check).

        Returns:
            Source video frame rate in frames per second, or None when it cannot be
            determined from the stored video metadata.
        """
        job = await self.job_repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            return None

        video = await self.video_repo.get_by_id(job.video_id)
        if not video:
            return None

        if video.fps:
            return float(video.fps)

        if video.frame_count and video.duration:
            return float(video.frame_count) / float(video.duration)

        return None

    async def get_job_results(self, job_id: str, user_id: str) -> JobResultsResponse:
        """
        Build the aggregated tracking statistics payload for a tracking job.

        Statistics are sourced from the persisted TrackResult row when available and
        are otherwise re-derived by parsing the MOT challenge artifact from disk.

        Args:
            job_id: Identifier of the tracking job.
            user_id: Identifier of the requesting user (ownership check).

        Returns:
            JobResultsResponse DTO describing track counts and artifact availability.

        Raises:
            HTTPException 404: If the job does not exist or belongs to another user.
        """
        job = await self.job_repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )

        artifacts = await self.get_job_artifacts(job_id, user_id)
        paths = artifacts["paths"]
        urls = artifacts["urls"]

        stats = parse_mot_results(paths["output_mot_path"])

        total_tracks = int(stats["total_tracks"])
        total_detections = int(stats["total_detections"])
        total_frames = int(stats["total_frames"])
        avg_track_length = float(stats["avg_track_length"])
        longest_track_frames = int(stats["longest_track_frames"])
        tracks: List[Dict] = list(stats["tracks"])
        fps = 0.0

        record = None
        if self.track_result_repo is not None:
            record = await self.track_result_repo.get_by_job_id(job_id)

        if record is not None:
            if hasattr(record, "total_tracks") and record.total_tracks:
                total_tracks = int(record.total_tracks)
            if hasattr(record, "fps") and record.fps:
                fps = float(record.fps)

            summary = getattr(record, "summary_json", None)
            if isinstance(summary, dict):
                total_detections = int(summary.get("total_detections", total_detections))
                total_frames = int(summary.get("total_frames", total_frames))
                avg_track_length = float(summary.get("avg_track_length", avg_track_length))
                longest_track_frames = int(
                    summary.get("longest_track_frames", longest_track_frames)
                )
                if summary.get("tracks"):
                    tracks = summary["tracks"]

        video = await self.video_repo.get_by_id(job.video_id)
        source_video_url = None
        if video and video.file_path:
            source_video_url = f"/uploads/{os.path.basename(video.file_path)}"

        return JobResultsResponse(
            job_id=job.id,
            status=job.status.value if hasattr(job.status, "value") else str(job.status),
            video_id=job.video_id,
            total_tracks=total_tracks,
            total_detections=total_detections,
            total_frames=total_frames,
            fps=fps,
            avg_track_length=avg_track_length,
            longest_track_frames=longest_track_frames,
            tracks=tracks,
            annotated_video_available=artifacts["annotated_video_available"],
            mot_results_available=artifacts["mot_results_available"],
            source_video_url=source_video_url,
            annotated_video_url=urls["annotated_video_url"],
            mot_results_url=urls["mot_results_url"],
            error_message=job.error_message,
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

    async def delete_job(self, job_id: str, user_id: str) -> dict:
        """
        Delete a TrackingJob record, clean up its disk artifacts, and cascade delete results.
        """
        job = await self.job_repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )

        # Remove physical disk artifacts
        paths = build_artifact_paths(job_id)
        temp_paths = build_artifact_temp_paths(job_id)
        for path in [
            paths.get("annotated_video_path"),
            paths.get("output_mot_path"),
            temp_paths.get("annotated_video_path"),
            temp_paths.get("output_mot_path"),
        ]:
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

        await self.job_repo.delete(job_id)
        return {"status": "deleted", "job_id": job_id}
