"""
Main ML Tracking Pipeline Orchestrator.
Coordinates Video Reading -> Detection -> DeepSORT Tracking -> Annotation -> File Output.
Pure Python module with zero dependencies on FastAPI, Redis, or PostgreSQL.
"""

from typing import Callable, Optional
import time

from ml.detectors.base import BaseDetector
from ml.detectors.yolo_detector import YOLOv8Detector
from ml.tracker.deep_sort import DeepSortTracker
from ml.types import FrameTrackingResult, PipelineResult
from ml.utils.draw import draw_tracks_on_frame, export_mot_results
from ml.utils.video_io import VideoReader, VideoWriter


class TrackingPipeline:
    """End-to-end video tracking pipeline."""

    def __init__(
        self,
        detector: Optional[BaseDetector] = None,
        tracker: Optional[DeepSortTracker] = None,
        detector_weights: str = "yolov8m.pt",
        conf_threshold: float = 0.5,
        reid_weights: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """
        Args:
            detector: Custom object detector instance (BaseDetector). Defaults to YOLOv8Detector if None.
            tracker: Custom DeepSORT tracker instance. Defaults to DeepSortTracker if None.
            detector_weights: YOLO model weight file path if default detector used.
            conf_threshold: Object detection confidence threshold.
            reid_weights: PyTorch model weight file path for Re-ID feature extractor.
            device: 'cuda', 'cpu', or auto.
        """
        if detector is None:
            self.detector = YOLOv8Detector(
                model_path=detector_weights,
                conf_threshold=conf_threshold,
                device=device,
            )
        else:
            self.detector = detector

        if tracker is None:
            self.tracker = DeepSortTracker(
                reid_model_path=reid_weights,
                device=device,
            )
        else:
            self.tracker = tracker

    def run(
        self,
        input_video_path: str,
        output_video_path: Optional[str] = None,
        output_mot_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        progress_interval: int = 10,
    ) -> PipelineResult:
        """Run tracking pipeline on input video file.

        Args:
            input_video_path: Path to input video file.
            output_video_path: Optional path to save annotated output video.
            output_mot_path: Optional path to save MOT format text file.
            progress_callback: Observer callback function `fn(current_frame, total_frames)`.
            progress_interval: Report progress every N frames.

        Returns:
            PipelineResult dataclass summarizing execution.
        """
        self.detector.warmup()

        frame_results = []
        all_track_ids = set()
        start_time = time.time()
        processed_count = 0

        with VideoReader(input_video_path) as reader:
            total_frames = reader.total_frames

            writer = None
            if output_video_path:
                writer = VideoWriter(
                    output_path=output_video_path,
                    fps=reader.fps,
                    width=reader.width,
                    height=reader.height,
                )

            try:
                for frame_idx, frame in reader:
                    processed_count += 1

                    # 1. Run detection on current frame
                    detections = self.detector.detect(frame)

                    # 2. Update DeepSORT tracker
                    tracks = self.tracker.update(detections, frame)

                    # 3. Store results
                    frame_results.append(
                        FrameTrackingResult(frame_idx=frame_idx, tracks=tracks)
                    )
                    for trk in tracks:
                        all_track_ids.add(trk.track_id)

                    # 4. Write annotated video frame if requested
                    if writer:
                        annotated_frame = draw_tracks_on_frame(frame, tracks)
                        writer.write_frame(annotated_frame)

                    # 5. Report progress to observer callback
                    if progress_callback and (
                        processed_count % progress_interval == 0
                        or processed_count == total_frames
                    ):
                        progress_callback(processed_count, total_frames)

            finally:
                if writer:
                    writer.release()

        elapsed_time = time.time() - start_time
        fps = processed_count / elapsed_time if elapsed_time > 0 else 0.0

        # Export MOT Challenge text format if output path specified
        if output_mot_path:
            export_mot_results(frame_results, output_mot_path)

        return PipelineResult(
            total_frames=total_frames,
            processed_frames=processed_count,
            total_tracks=len(all_track_ids),
            fps=fps,
            output_video_path=output_video_path,
            output_mot_path=output_mot_path,
        )
