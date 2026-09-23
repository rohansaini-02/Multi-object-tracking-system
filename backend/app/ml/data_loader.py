"""
Frame and Sequence Data Loader for Videos & MOT17 Datasets (Week 2 Milestone).
"""

import os
from typing import Generator, List, Tuple
import cv2
import numpy as np


class VideoDataLoader:
    """Frame extraction loader for video files."""

    def __init__(self, video_path: str):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")
        self.video_path = video_path
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            raise ValueError(f"Unable to open video stream: {video_path}")

        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def read_frames(self) -> Generator[Tuple[int, np.ndarray], None, None]:
        """Iterate over frames yielding 1-based (frame_index, frame_bgr_array)."""
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


class MOT17SequenceDataLoader:
    """Frame extraction loader for MOT17 benchmark sequence image folders."""

    def __init__(self, sequence_dir: str):
        self.sequence_dir = sequence_dir
        self.img_dir = os.path.join(sequence_dir, "img1")
        if not os.path.exists(self.img_dir):
            raise FileNotFoundError(f"MOT17 img1 directory not found at: {self.img_dir}")

        self.image_files = sorted([
            f for f in os.listdir(self.img_dir)
            if f.lower().endswith((".jpg", ".png", ".jpeg"))
        ])
        if len(self.image_files) == 0:
            raise ValueError(f"No image files found in sequence directory: {self.img_dir}")

        # Read first frame to extract dimensions
        first_img_path = os.path.join(self.img_dir, self.image_files[0])
        first_img = cv2.imread(first_img_path)
        if first_img is None:
            raise ValueError(f"Unable to read image file: {first_img_path}")
        self.height, self.width, _ = first_img.shape
        self.total_frames = len(self.image_files)

    def read_frames(self) -> Generator[Tuple[int, np.ndarray], None, None]:
        """Yield 1-based (frame_index, frame_bgr_array)."""
        for idx, filename in enumerate(self.image_files, start=1):
            img_path = os.path.join(self.img_dir, filename)
            frame = cv2.imread(img_path)
            if frame is not None:
                yield idx, frame
