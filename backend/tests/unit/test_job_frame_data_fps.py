"""
Unit Test Suite for the frame rate published by the tracking-job frame payload.

``GET /jobs/{job_id}/frames`` returns the frame-indexed bounding boxes that the
frontend overlays on the source video. The client maps the video timeline onto
the frame indices with that payload's ``fps`` value, so ``fps`` has to be the
frame rate of the *source video*.

The persisted track-result row stores the pipeline *processing throughput*
(frames per second the tracker managed to process), which is a completely
different quantity. Publishing it as ``fps`` shifted every overlay box onto the
wrong frame - a 25 fps clip processed at 4 fps made the UI read frame 4 when it
should have read frame 25.

These tests pin the source-video frame rate down and guard the regression.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

import pytest

from backend.app.api import jobs as jobs_api
from backend.app.services.job_service import JobService


class _FakeJob:
    """Minimal stand-in for a TrackingJob record."""

    def __init__(self, job_id="job-1", user_id="user-1", video_id="vid-1"):
        self.id = job_id
        self.user_id = user_id
        self.video_id = video_id


class _FakeVideo:
    """Minimal stand-in for a Video record."""

    def __init__(self, fps: Optional[float] = None, duration=None, frame_count=None):
        self.id = "vid-1"
        self.fps = fps
        self.duration = duration
        self.frame_count = frame_count


class _FakeJobRepo:
    def __init__(self, job):
        self._job = job

    async def get_by_id(self, job_id):
        return self._job if self._job and self._job.id == job_id else None


class _FakeVideoRepo:
    def __init__(self, video):
        self._video = video

    async def get_by_id(self, video_id):
        return self._video if self._video and self._video.id == video_id else None


def _service(video, job=None):
    job = job or _FakeJob()
    return JobService(_FakeJobRepo(job), _FakeVideoRepo(video))


@pytest.mark.asyncio
async def test_source_video_fps_comes_from_the_stored_video_metadata():
    service = _service(_FakeVideo(fps=25.0))
    assert await service.get_source_video_fps("job-1", "user-1") == 25.0


@pytest.mark.asyncio
async def test_source_video_fps_falls_back_to_frame_count_over_duration():
    service = _service(_FakeVideo(fps=None, duration=4.0, frame_count=100))
    assert await service.get_source_video_fps("job-1", "user-1") == 25.0


@pytest.mark.asyncio
async def test_source_video_fps_is_none_without_any_metadata():
    service = _service(_FakeVideo(fps=None, duration=None, frame_count=None))
    assert await service.get_source_video_fps("job-1", "user-1") is None


@pytest.mark.asyncio
async def test_source_video_fps_is_none_for_a_job_of_another_user():
    service = _service(_FakeVideo(fps=25.0))
    assert await service.get_source_video_fps("job-1", "somebody-else") is None


@pytest.mark.asyncio
async def test_source_video_fps_is_none_for_an_unknown_job():
    service = _service(_FakeVideo(fps=25.0))
    assert await service.get_source_video_fps("does-not-exist", "user-1") is None


def test_frames_endpoint_reports_the_source_video_frame_rate(monkeypatch):
    """The endpoint must publish the source fps, never the processing throughput."""
    # A private temporary directory keeps this test independent of pytest's
    # own temp root, which is not always writable on shared Windows machines.
    with tempfile.TemporaryDirectory() as tmpdir:
        mot_file = Path(tmpdir) / "job-1_mot.txt"
        mot_file.write_text(
            "1,1,100.0,200.0,40.0,80.0,0.9,-1,-1,-1\n"
            "2,1,110.0,200.0,40.0,80.0,0.9,-1,-1,-1\n",
            encoding="utf-8",
        )

        service = _service(_FakeVideo(fps=25.0))

        async def fake_artifacts(job_id, user_id):
            return {"paths": {"output_mot_path": str(mot_file)}}

        monkeypatch.setattr(service, "get_job_artifacts", fake_artifacts)
        monkeypatch.setattr(jobs_api, "_build_service", lambda session: service)

        payload = asyncio.run(
            jobs_api.get_job_frame_data(
                "job-1", current_user=type("U", (), {"id": "user-1"})()
            )
        )

    assert payload["fps"] == 25.0
    assert payload["total_frames"] == 2
    assert set(payload["frames"]) == {"1", "2"}


def test_frames_endpoint_falls_back_to_30_fps_without_video_metadata(monkeypatch):
    """A clip whose metadata carries no frame rate must not break the client."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mot_file = Path(tmpdir) / "job-1_mot.txt"
        mot_file.write_text("1,1,100.0,200.0,40.0,80.0,0.9,-1,-1,-1\n", encoding="utf-8")

        service = _service(_FakeVideo(fps=None, duration=None, frame_count=None))

        async def fake_artifacts(job_id, user_id):
            return {"paths": {"output_mot_path": str(mot_file)}}

        monkeypatch.setattr(service, "get_job_artifacts", fake_artifacts)
        monkeypatch.setattr(jobs_api, "_build_service", lambda session: service)

        payload = asyncio.run(
            jobs_api.get_job_frame_data(
                "job-1", current_user=type("U", (), {"id": "user-1"})()
            )
        )

    assert payload["fps"] == 30.0
