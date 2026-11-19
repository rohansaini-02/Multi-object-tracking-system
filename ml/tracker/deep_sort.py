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

# Maximum (1 - IoU) spatial cost tolerated by the fallback spatial association stage.
# A cost of 0.7 corresponds to the classic DeepSORT requirement that a detection
# overlaps a predicted track box by at least 30%.
DEFAULT_MAX_IOU_DISTANCE = 0.7

# Number of consecutive missed frames a TENTATIVE track survives before it is
# discarded. A tentative track holds a single observation, therefore its Kalman
# velocity estimate is still zero and its predicted box does not move. Deleting
# it on the very first miss would burn a brand new track id for an object that
# was merely occluded for a single frame.
DEFAULT_MAX_TENTATIVE_AGE = 3


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
        max_tentative_age: int = DEFAULT_MAX_TENTATIVE_AGE,
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
        self._max_tentative_age = max_tentative_age
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
            # A tentative track carries a single observation and no velocity
            # estimate, so it needs several chances to be re-acquired before its
            # identity is thrown away. Without this grace period every brief
            # dropout mints a brand new track id.
            if self.time_since_update > self._max_tentative_age:
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
        max_iou_distance: float = DEFAULT_MAX_IOU_DISTANCE,
        max_tentative_age: int = DEFAULT_MAX_TENTATIVE_AGE,
    ):
        self.max_cosine_distance = max_cosine_distance
        self.nn_budget = nn_budget
        self.max_age = max_age
        self.n_init = n_init
        self.max_iou_distance = max_iou_distance
        self.max_tentative_age = max_tentative_age

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
        """Associate tracks with detections using three ordered stages.

        1. **Cascaded appearance matching** for confirmed tracks (classic DeepSORT).
           Tracks are served newest-first so a well-established identity never
           loses its detection to a younger track.
        2. **Spatial (IoU) matching** for every track the cascade could not place,
           confirmed or tentative.
        3. **Appearance matching** for the tentative tracks stage 2 could not place.
           A tentative track holds a single observation, so its Kalman velocity
           estimate is still zero and its predicted box does not move; the IoU
           gate of stage 2 therefore rejects any object that moves faster than
           roughly a third of its own box size. Appearance is motion invariant,
           so it re-establishes the identity in exactly that case and stops the
           tracker from minting a brand new id on every single frame.
        """
        confirmed_tracks = [
            i for i, t in enumerate(self.tracks) if t.is_confirmed()
        ]
        tentative_tracks = [
            i for i, t in enumerate(self.tracks) if t.is_tentative()
        ]

        # Stage 1: Cascaded matching on confirmed tracks using appearance features
        matches_a, unmatched_tracks_a, unmatched_detections = self._match_by_cascade(
            detections, confirmed_tracks
        )

        # Stage 2: IoU matching for unconfirmed tracks & unmatched confirmed tracks
        matches_b, unmatched_tracks_b, unmatched_detections = self._match_by_overlap(
            detections, unmatched_tracks_a + tentative_tracks, unmatched_detections
        )

        # Stage 3: appearance matching for the tentative tracks the IoU gate
        # rejected. Only genuinely unclaimed detections reach this stage: the
        # confirmed tracks were served first by stages 1 and 2.
        still_tentative = [i for i in tentative_tracks if i in unmatched_tracks_b]
        matches_c, _, unmatched_detections = self._match_by_appearance(
            detections, still_tentative, unmatched_detections
        )

        matches = matches_a + matches_b + matches_c
        matched_tracks = {track_idx for track_idx, _ in matches}
        unmatched_tracks = [i for i in unmatched_tracks_b if i not in matched_tracks]
        return matches, unmatched_tracks, unmatched_detections

    def _match_by_cascade(
        self, detections: List[Detection], confirmed_tracks: List[int]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Stage 1: cascaded appearance matching for the confirmed tracks."""
        return matching_cascade(
            cosine_distance_matrix,
            self.max_cosine_distance,
            self.max_age,
            self.tracks,
            detections,
            confirmed_tracks,
        )

    def _match_by_overlap(
        self,
        detections: List[Detection],
        track_indices: List[int],
        detection_indices: List[int],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Stage 2: spatial (IoU) matching for the tracks the cascade could not place."""
        return min_cost_matching(
            iou_cost_matrix,
            max_distance=self.max_iou_distance,
            tracks=self.tracks,
            detections=detections,
            track_indices=track_indices,
            detection_indices=detection_indices,
        )

    def _match_by_appearance(
        self,
        detections: List[Detection],
        track_indices: List[int],
        detection_indices: List[int],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Stage 3: appearance matching for the tentative tracks the IoU gate rejected."""
        return min_cost_matching(
            cosine_distance_matrix,
            max_distance=self.max_cosine_distance,
            tracks=self.tracks,
            detections=detections,
            track_indices=track_indices,
            detection_indices=detection_indices,
        )

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
            max_tentative_age=self.max_tentative_age,
        )
        self.tracks.append(track)
        self._next_id += 1
