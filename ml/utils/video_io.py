"""
Video reading and writing utilities using OpenCV.
"""

import os
from typing import Generator, Tuple
import cv2
import numpy as np


class VideoReader:
    """Helper for reading video frames iteratively using OpenCV."""

    def __init__(self, video_path: str):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        self.video_path = video_path
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def __iter__(self) -> Generator[Tuple[int, np.ndarray], None, None]:
        """Iterate over frames yielding (frame_index_1_based, frame_bgr_array)."""
        frame_idx = 1
        while self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret or frame is None:
                break
            yield frame_idx, frame
            frame_idx += 1

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class VideoWriter:
    """Helper for writing annotated video frames using OpenCV."""

    def __init__(self, output_path: str, fps: float, width: int, height: int, fourcc_str: str = "mp4v"):
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.output_path = output_path
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        self._writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not self._writer.isOpened():
            # Fallback to avc1 if mp4v fails
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            self._writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    def write_frame(self, frame: np.ndarray) -> None:
        self._writer.write(frame)

    def release(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None

        # Automatically transcode to web-compatible H.264 (yuv420p) for HTML5 video playback
        try:
            import subprocess
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                temp_h264 = self.output_path + ".h264.mp4"
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-i", self.output_path,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "fast",
                    temp_h264
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res.returncode == 0 and os.path.exists(temp_h264) and os.path.getsize(temp_h264) > 0:
                    os.replace(temp_h264, self.output_path)
                elif os.path.exists(temp_h264):
                    os.remove(temp_h264)
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

