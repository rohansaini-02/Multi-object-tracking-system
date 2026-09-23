"""
End-to-End Multi-Object Tracking Pipeline Coordinator (Week 4 Milestone).

Coordinates:
  VideoDataLoader -> YOLOv8Detector -> ReidFeatureExtractor -> KalmanFilter -> Hungarian Cascade -> VideoWriter/MOT Exporter
"""

from typing import Callable, Optional
import logging
import time

from backend.app.ml.data_loader import VideoDataLoader
from backend.app.ml.detector import YOLOv8Detector
from backend.app.ml.reid import ReidFeatureExtractor
from backend.app.ml.tracker import Tracker
from ml.types import FrameTrackingResult, PipelineResult
from ml.utils.draw import draw_tracks_on_frame, export_mot_results
from ml.utils.video_io import VideoWriter

logger = logging.getLogger(__name__)


class TrackingPipeline:
    """End-to-end video tracking pipeline manager."""

    def __init__(
        self,
        detector_weights: str = "weights/yolov8m.pt",
        conf_threshold: float = 0.25,
        reid_weights: Optional[str] = None,
        max_age: int = 30,
        n_init: int = 1,
        max_cosine_distance: float = 0.2,
        device: Optional[str] = None,
    ):
        """
        Args:
            detector_weights: Path to YOLO detection model weights file.
            conf_threshold: Detection confidence threshold score [0.0, 1.0].
            reid_weights: Path to fine-tuned PyTorch Re-ID model weights (.pth).
            max_age: Maximum coasting frames before track deletion.
            n_init: Number of consecutive matches needed to confirm track.
            max_cosine_distance: Appearance feature matching distance threshold.
            device: 'cuda', 'cpu', or auto.
        """
        self.detector = YOLOv8Detector(
            model_path=detector_weights,
            conf_threshold=conf_threshold,
            device=device,
        )
        self.reid_extractor = ReidFeatureExtractor(
            model_path=reid_weights,
            device=device,
        )
        self.tracker = Tracker(
            max_age=max_age,
            n_init=n_init,
        )
        self.max_cosine_distance = max_cosine_distance

    def run(
        self,
        input_video_path: str,
        output_video_path: Optional[str] = None,
        output_mot_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        progress_interval: int = 10,
    ) -> PipelineResult:
        """Process video through detector, Re-ID extractor, Kalman filter, and Hungarian cascade.

        Args:
            input_video_path: Path to input video file on disk.
            output_video_path: Optional output file path for annotated video.
            output_mot_path: Optional output file path for MOT Challenge text file.
            progress_callback: Observer callback function `fn(current_frame, total_frames)`.
            progress_interval: Callback reporting frequency interval (default: every 10 frames).

        Returns:
            PipelineResult dataclass summarizing execution statistics.
        """
        logger.info("Warming up detector models...")
        self.detector.warmup()

        frame_results = []
        all_track_ids = set()
        start_time = time.time()
        processed_count = 0

        with VideoDataLoader(input_video_path) as loader:
            total_frames = loader.total_frames

            writer = None
            if output_video_path:
                writer = VideoWriter(
                    output_path=output_video_path,
                    fps=loader.fps,
                    width=loader.width,
                    height=loader.height,
                )

            try:
                for frame_idx, frame in loader.read_frames():
                    processed_count += 1

                    # 1. Run YOLOv8 object detection
                    detections = self.detector.detect(frame)

                    # 2. Extract PyTorch L2-normalized appearance embeddings
                    detections = self.reid_extractor.extract(frame, detections)

                    # 3. Predict Kalman filter motion step for existing tracks
                    self.tracker.predict()

                    # 4. Associate tracks with detections using Hungarian cascade
                    # Import matching methods dynamically
                    from backend.app.ml.hungarian import (
                        compute_cosine_distance_matrix,
                        compute_iou_cost_matrix,
                        solve_matching_cascade,
                        solve_hungarian_matching,
                    )

                    confirmed_indices = [
                        i for i, t in enumerate(self.tracker.tracks) if t.is_confirmed()
                    ]
                    unconfirmed_indices = [
                        i for i, t in enumerate(self.tracker.tracks) if not t.is_confirmed()
                    ]

                    # Stage 1: Cascaded matching on confirmed tracks using appearance features
                    matches_a, unmatched_tracks_a, unmatched_detections = solve_matching_cascade(
                        compute_cosine_distance_matrix,
                        self.max_cosine_distance,
                        self.tracker.max_age,
                        self.tracker.tracks,
                        detections,
                        confirmed_indices,
                    )

                    # Stage 2: IoU matching fallback for unconfirmed & unmatched tracks
                    iou_track_candidates = unmatched_tracks_a + unconfirmed_indices
                    matches_b, unmatched_tracks_b, unmatched_detections = solve_hungarian_matching(
                        compute_iou_cost_matrix,
                        0.7,
                        self.tracker.tracks,
                        detections,
                        iou_track_candidates,
                        unmatched_detections,
                    )

                    matches = matches_a + matches_b

                    # Update matched tracks
                    for trk_idx, det_idx in matches:
                        self.tracker.tracks[trk_idx].update(self.tracker.kf, detections[det_idx])

                    # Mark missed tracks
                    for trk_idx in unmatched_tracks_b:
                        self.tracker.tracks[trk_idx].mark_missed()

                    # Initiate new tentative tracks from unmatched detections
                    for det_idx in unmatched_detections:
                        self.tracker.initiate_track(detections[det_idx])

                    # Purge deleted tracks
                    self.tracker.purge_deleted_tracks()

                    # 5. Extract active confirmed outputs
                    active_outputs = []
                    for t in self.tracker.tracks:
                        if t.is_confirmed() and t.time_since_update <= 1:
                            out = t.to_tlwh_bbox()
                            from ml.types import TrackOutput
                            active_outputs.append(
                                TrackOutput(
                                    track_id=t.track_id,
                                    bbox=out,
                                    confidence=t.confidence,
                                    class_id=t.class_id,
                                    state=t.state,
                                )
                            )
                            all_track_ids.add(t.track_id)

                    frame_results.append(
                        FrameTrackingResult(frame_idx=frame_idx, tracks=active_outputs)
                    )

                    # 6. Write annotated video frame
                    if writer:
                        annotated_frame = draw_tracks_on_frame(frame, active_outputs)
                        writer.write_frame(annotated_frame)

                    # 7. Report progress to observer callback
                    if progress_callback and (
                        processed_count % progress_interval == 0
                        or processed_count == total_frames
                    ):
                        progress_callback(processed_count, total_frames)

            finally:
                if writer:
                    writer.release()

        elapsed = time.time() - start_time
        fps = processed_count / elapsed if elapsed > 0 else 0.0

        if output_mot_path:
            export_mot_results(frame_results, output_mot_path)

        logger.info(
            "Pipeline completed: %d frames, %d unique tracks, %.2f FPS",
            processed_count,
            len(all_track_ids),
            fps,
        )

        return PipelineResult(
            total_frames=total_frames,
            processed_frames=processed_count,
            total_tracks=len(all_track_ids),
            fps=fps,
            output_video_path=output_video_path,
            output_mot_path=output_mot_path,
        )
