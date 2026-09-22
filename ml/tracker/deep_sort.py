"""
DeepSORT Tracker Coordinator & Track Lifecycle Manager.
"""

from typing import List, Optional, Tuple
import numpy as np

from ml.tracker.kalman_filter import KalmanFilter
from ml.tracker.reid_feature_extractor import ReidFeatureExtractor
from ml.tracker.matching import (
    cosine_distance_matrix,
    iou_cost_matrix,
    min_cost_matching,
    matching_cascade,
)
from ml.types import BoundingBox, Detection, TrackOutput, TrackState


class Track:
    """A single object track state managed by Kalman Filter & Feature Gallery."""

    def __init__(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        track_id: int,
        n_init: int,
        max_age: int,
        feature: Optional[np.ndarray] = None,
        class_id: int = 0,
        confidence: float = 1.0,
    ):
        self.mean = mean
        self.covariance = covariance
        self.track_id = track_id
        self.hits = 1
        self.age = 1
        self.time_since_update = 0
        self.state = TrackState.TENTATIVE
        self.features: List[np.ndarray] = []
        if feature is not None:
            self.features.append(feature)

        self._n_init = n_init
        self._max_age = max_age
        self.class_id = class_id
        self.confidence = confidence

    def predict(self, kf: KalmanFilter) -> None:
        """Propagate track state mean and covariance using Kalman Filter."""
        self.mean, self.covariance = kf.predict(self.mean, self.covariance)
        self.age += 1
        self.time_since_update += 1

    def update(
        self,
        kf: KalmanFilter,
        detection: Detection,
    ) -> None:
        """Update track with matched detection."""
        measurement = detection.bbox.to_xyah()
        self.mean, self.covariance = kf.update(self.mean, self.covariance, measurement)
        
        if detection.feature is not None:
            self.features.append(detection.feature)

        self.hits += 1
        self.time_since_update = 0
        self.confidence = detection.confidence
        self.class_id = detection.class_id

        if self.state == TrackState.TENTATIVE and self.hits >= self._n_init:
            self.state = TrackState.CONFIRMED

    def mark_missed(self) -> None:
        """Mark track as missed in current frame."""
        if self.state == TrackState.TENTATIVE:
            self.state = TrackState.DELETED
        elif self.time_since_update > self._max_age:
            self.state = TrackState.DELETED

    def is_tentative(self) -> bool:
        return self.state == TrackState.TENTATIVE

    def is_confirmed(self) -> bool:
        return self.state == TrackState.CONFIRMED

    def is_deleted(self) -> bool:
        return self.state == TrackState.DELETED

    def to_tlwh_bbox(self) -> BoundingBox:
        """Extract BoundingBox from current mean state [cx, cy, a, h]."""
        cx, cy, a, h = self.mean[:4]
        return BoundingBox.from_xyah(cx, cy, a, h)


class DeepSortTracker:
    """DeepSORT Tracker coordinating Kalman filtering, Re-ID extraction, and Cascaded matching."""

    def __init__(
        self,
        max_cosine_distance: float = 0.2,
        nn_budget: int = 100,
        max_age: int = 30,
        n_init: int = 3,
        reid_model_path: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.max_cosine_distance = max_cosine_distance
        self.nn_budget = nn_budget
        self.max_age = max_age
        self.n_init = n_init

        self.kf = KalmanFilter()
        self.reid_extractor = ReidFeatureExtractor(
            model_path=reid_model_path, device=device
        )
        self.tracks: List[Track] = []
        self._next_id = 1

    def update(
        self, detections: List[Detection], frame: np.ndarray
    ) -> List[TrackOutput]:
        """Process detections for current frame and return active confirmed tracks.

        Args:
            detections: Detections from ObjectDetector.
            frame: Current frame BGR image array.

        Returns:
            List of TrackOutput objects for confirmed tracks.
        """
        # 1. Extract Re-ID appearance features for all detections
        detections = self.reid_extractor.extract(frame, detections)

        # 2. Kalman filter predict step for existing tracks
        for track in self.tracks:
            track.predict(self.kf)

        # 3. Associate tracks with detections
        matches, unmatched_tracks, unmatched_detections = self._match(detections)

        # 4. Update matched tracks
        for track_idx, det_idx in matches:
            self.tracks[track_idx].update(self.kf, detections[det_idx])

        # 5. Handle unmatched tracks
        for track_idx in unmatched_tracks:
            self.tracks[track_idx].mark_missed()

        # 6. Initiate new tentative tracks from unmatched detections
        for det_idx in unmatched_detections:
            self._initiate_track(detections[det_idx])

        # 7. Remove deleted tracks & trim feature galleries to nn_budget
        self.tracks = [t for t in self.tracks if not t.is_deleted()]
        for track in self.tracks:
            if len(track.features) > self.nn_budget:
                track.features = track.features[-self.nn_budget:]

        # 8. Return outputs for active confirmed tracks
        outputs = []
        for track in self.tracks:
            if track.is_confirmed() and track.time_since_update <= 1:
                outputs.append(
                    TrackOutput(
                        track_id=track.track_id,
                        bbox=track.to_tlwh_bbox(),
                        confidence=track.confidence,
                        class_id=track.class_id,
                        state=track.state,
                    )
                )

        return outputs

    def _match(
        self, detections: List[Detection]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Perform two-stage matching: (1) Cascaded cosine matching for confirmed tracks, (2) IoU matching for remaining."""
        confirmed_tracks = [
            i for i, t in enumerate(self.tracks) if t.is_confirmed()
        ]
        unconfirmed_tracks = [
            i for i, t in enumerate(self.tracks) if not t.is_confirmed()
        ]

        # Stage 1: Cascaded matching on confirmed tracks using appearance features
        matches_a, unmatched_tracks_a, unmatched_detections = matching_cascade(
            cosine_distance_matrix,
            self.max_cosine_distance,
            self.max_age,
            self.tracks,
            detections,
            confirmed_tracks,
        )

        # Stage 2: IoU matching for unconfirmed tracks & unmatched confirmed tracks
        iou_track_candidates = unmatched_tracks_a + unconfirmed_tracks
        matches_b, unmatched_tracks_b, unmatched_detections = min_cost_matching(
            iou_cost_matrix,
            max_distance=0.7,  # Max 1 - IoU distance threshold
            tracks=self.tracks,
            detections=detections,
            track_indices=iou_track_candidates,
            detection_indices=unmatched_detections,
        )

        matches = matches_a + matches_b
        unmatched_tracks = unmatched_tracks_b
        return matches, unmatched_tracks, unmatched_detections

    def _initiate_track(self, detection: Detection) -> None:
        """Create a new tentative track from unassociated detection."""
        measurement = detection.bbox.to_xyah()
        mean, covariance = self.kf.initiate(measurement)
        track = Track(
            mean=mean,
            covariance=covariance,
            track_id=self._next_id,
            n_init=self.n_init,
            max_age=self.max_age,
            feature=detection.feature,
            class_id=detection.class_id,
            confidence=detection.confidence,
        )
        self.tracks.append(track)
        self._next_id += 1
