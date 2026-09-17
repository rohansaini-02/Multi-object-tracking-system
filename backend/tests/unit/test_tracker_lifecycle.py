"""
Unit Tests for Track Lifecycle State Machine (Week 3 Milestone).
"""

unittest_module = True
import unittest
import numpy as np

from ml.types import BoundingBox, Detection, TrackState
from backend.app.ml.kalman import KalmanFilter
from backend.app.ml.tracker import Track, Tracker


class TestTrackLifecycle(unittest.TestCase):
    def setUp(self):
        self.kf = KalmanFilter()

    def test_track_initial_state_tentative(self):
        """Verify new track starts in TENTATIVE state with hits=1."""
        measurement = np.array([100.0, 100.0, 0.5, 50.0], dtype=np.float32)
        mean, covariance = self.kf.initiate(measurement)
        track = Track(mean=mean, covariance=covariance, track_id=1, n_init=3, max_age=30)

        self.assertTrue(track.is_tentative())
        self.assertFalse(track.is_confirmed())
        self.assertFalse(track.is_deleted())
        self.assertEqual(track.hits, 1)

    def test_tentative_to_confirmed_transition(self):
        """Verify track transitions to CONFIRMED when hits >= n_init."""
        measurement = np.array([100.0, 100.0, 0.5, 50.0], dtype=np.float32)
        mean, covariance = self.kf.initiate(measurement)
        track = Track(mean=mean, covariance=covariance, track_id=1, n_init=3, max_age=30)

        # Hit 2
        det2 = Detection(bbox=BoundingBox(75.0, 75.0, 125.0, 125.0), confidence=0.9)
        track.predict(self.kf)
        track.update(self.kf, det2)
        self.assertEqual(track.hits, 2)
        self.assertTrue(track.is_tentative())

        # Hit 3 (n_init reached)
        det3 = Detection(bbox=BoundingBox(75.0, 75.0, 125.0, 125.0), confidence=0.9)
        track.predict(self.kf)
        track.update(self.kf, det3)
        self.assertEqual(track.hits, 3)
        self.assertTrue(track.is_confirmed())
        self.assertFalse(track.is_tentative())

    def test_tentative_missed_deletion(self):
        """Verify tentative track is deleted immediately if it misses a frame."""
        measurement = np.array([100.0, 100.0, 0.5, 50.0], dtype=np.float32)
        mean, covariance = self.kf.initiate(measurement)
        track = Track(mean=mean, covariance=covariance, track_id=1, n_init=3, max_age=30)

        track.predict(self.kf)
        track.mark_missed()
        self.assertTrue(track.is_deleted())

    def test_confirmed_coasting_and_max_age_deletion(self):
        """Verify confirmed track coasts up to max_age missed frames before deletion."""
        measurement = np.array([100.0, 100.0, 0.5, 50.0], dtype=np.float32)
        mean, covariance = self.kf.initiate(measurement)
        track = Track(mean=mean, covariance=covariance, track_id=1, n_init=1, max_age=3)

        # Immediate confirmation (n_init=1)
        det = Detection(bbox=BoundingBox(75.0, 75.0, 125.0, 125.0), confidence=0.9)
        track.update(self.kf, det)
        self.assertTrue(track.is_confirmed())

        # Coasting frame 1
        track.predict(self.kf)
        track.mark_missed()
        self.assertTrue(track.is_confirmed())

        # Coasting frame 2
        track.predict(self.kf)
        track.mark_missed()
        self.assertTrue(track.is_confirmed())

        # Coasting frame 3
        track.predict(self.kf)
        track.mark_missed()
        self.assertTrue(track.is_confirmed())

        # Coasting frame 4 (> max_age 3) -> Deleted
        track.predict(self.kf)
        track.mark_missed()
        self.assertTrue(track.is_deleted())

    def test_tracker_coordinator_initiation_and_purge(self):
        """Test Tracker coordinator tracks management and purging of deleted tracks."""
        tracker = Tracker(max_age=30, n_init=3)
        det = Detection(bbox=BoundingBox(10.0, 10.0, 50.0, 50.0), confidence=0.85)

        track = tracker.initiate_track(det)
        self.assertEqual(len(tracker.tracks), 1)
        self.assertEqual(track.track_id, 1)

        # Mark missed -> tentative track marked deleted
        track.mark_missed()
        tracker.purge_deleted_tracks()
        self.assertEqual(len(tracker.tracks), 0)


if __name__ == "__main__":
    unittest.main()
