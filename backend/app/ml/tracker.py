"""
Track Lifecycle State Machine & DeepSORT Tracker Coordinator (Week 3 Milestone).

State Machine Transitions:
  [ Unassociated Detection ] ──► TENTATIVE (hits = 1, age = 1)
                                      │
                 Hits >= n_init       │   Missed frame before n_init
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
          CONFIRMED                                       DELETED
               │
   Missed > max_age frames (Coasting limit)
               │
               ▼
            DELETED
"""

import enum
import logging
from typing import List, Optional, Tuple
import numpy as np

from ml.types import BoundingBox, Detection, TrackOutput, TrackState
from backend.app.ml.kalman import KalmanFilter

logger = logging.getLogger(__name__)


class Track:
    """Represents a single tracked object state managed through Kalman Filter and lifecycle bounds."""

    def __init__(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        track_id: int,
        n_init: int = 3,
        max_age: int = 30,
        feature: Optional[np.ndarray] = None,
        class_id: int = 0,
        confidence: float = 1.0,
    ):
        """
        Args:
            mean: Initial 8-dim state mean vector from Kalman filter.
            covariance: Initial 8x8 state covariance matrix.
            track_id: Unique positive integer identifier.
            n_init: Number of consecutive detection hits required to confirm track.
            max_age: Maximum coasting frames (missed detections) before deletion.
            feature: Initial appearance feature embedding (optional).
            class_id: Class label integer (0 = person).
            confidence: Initial detection confidence score.
        """
        self.mean = mean
        self.covariance = covariance
        self.track_id = track_id
        self.hits = 1
        self.age = 1
        self.time_since_update = 0
        self.state = TrackState.CONFIRMED if self.hits >= n_init else TrackState.TENTATIVE

        self.features: List[np.ndarray] = []
        if feature is not None:
            self.features.append(feature)

        self._n_init = n_init
        self._max_age = max_age
        self.class_id = class_id
        self.confidence = confidence

    def predict(self, kf: KalmanFilter) -> None:
        """Propagate track state mean and covariance forward using Kalman filter."""
        self.mean, self.covariance = kf.predict(self.mean, self.covariance)
        self.age += 1
        self.time_since_update += 1

    def update(self, kf: KalmanFilter, detection: Detection) -> None:
        """Update track state with a matched detection measurement.

        Transitions TENTATIVE -> CONFIRMED if hits >= n_init.
        """
        measurement = detection.bbox.to_xyah()
        self.mean, self.covariance = kf.update(self.mean, self.covariance, measurement)

        if detection.feature is not None:
            self.features.append(detection.feature)

        self.hits += 1
        self.time_since_update = 0
        self.confidence = detection.confidence
        self.class_id = detection.class_id

        # State transition rule: Tentative -> Confirmed
        if self.state == TrackState.TENTATIVE and self.hits >= self._n_init:
            self.state = TrackState.CONFIRMED
            logger.debug("Track ID %d transitioned to CONFIRMED (hits=%d)", self.track_id, self.hits)

    def mark_missed(self) -> None:
        """Mark track as unassociated (coasting) in current frame."""
        if self.state == TrackState.TENTATIVE:
            self.state = TrackState.DELETED
            logger.debug("Tentative Track ID %d deleted due to missed detection", self.track_id)
        elif self.time_since_update > self._max_age:
            self.state = TrackState.DELETED
            logger.debug("Confirmed Track ID %d deleted after exceeding max_age (%d)", self.track_id, self._max_age)

    def is_tentative(self) -> bool:
        return self.state == TrackState.TENTATIVE

    def is_confirmed(self) -> bool:
        return self.state == TrackState.CONFIRMED

    def is_deleted(self) -> bool:
        return self.state == TrackState.DELETED

    def to_tlwh_bbox(self) -> BoundingBox:
        """Extract BoundingBox from current 8-dim state mean [cx, cy, a, h]."""
        cx, cy, a, h = self.mean[:4]
        return BoundingBox.from_xyah(cx, cy, a, h)


class Tracker:
    """Manages active track collection and coordinates lifecycle state transitions."""

    def __init__(
        self,
        max_age: int = 30,
        n_init: int = 1,
    ):
        """
        Args:
            max_age: Maximum coasting frames before track deletion.
            n_init: Number of consecutive matches needed to confirm track.
        """
        self.max_age = max_age
        self.n_init = n_init
        self.kf = KalmanFilter()
        self.tracks: List[Track] = []
        self._next_id = 1

    def predict(self) -> None:
        """Propagate all active tracks forward by one timestep."""
        for track in self.tracks:
            track.predict(self.kf)

    def initiate_track(self, detection: Detection) -> Track:
        """Initiate a new tentative track from an unassociated detection."""
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
        logger.debug("Initiated new TENTATIVE track ID %d", track.track_id)
        return track

    def purge_deleted_tracks(self) -> None:
        """Remove tracks in DELETED state from active list."""
        self.tracks = [t for t in self.tracks if not t.is_deleted()]
