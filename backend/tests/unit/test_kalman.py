"""
Unit Tests for 8-State Kalman Filter (Week 3 Milestone).
"""

import unittest
import numpy as np

from backend.app.ml.kalman import KalmanFilter


class TestKalmanFilter(unittest.TestCase):
    def setUp(self):
        self.kf = KalmanFilter()

    def test_initiate(self):
        """Test Kalman filter state initiation from 4-dim measurement [cx, cy, a, h]."""
        measurement = np.array([100.0, 200.0, 0.5, 80.0], dtype=np.float32)
        mean, covariance = self.kf.initiate(measurement)

        # State mean vector should be 8-dimensional
        self.assertEqual(mean.shape, (8,))
        # Covariance matrix should be 8x8
        self.assertEqual(covariance.shape, (8, 8))

        # Position states should match measurement
        np.testing.assert_allclose(mean[:4], measurement)
        # Velocity states should be initialized to 0
        np.testing.assert_allclose(mean[4:], np.zeros(4))

    def test_predict_and_update(self):
        """Test prediction propagation and measurement update steps."""
        measurement1 = np.array([100.0, 200.0, 0.5, 80.0], dtype=np.float32)
        mean, covariance = self.kf.initiate(measurement1)

        # Predict next state
        pred_mean, pred_cov = self.kf.predict(mean, covariance)
        self.assertEqual(pred_mean.shape, (8,))
        self.assertEqual(pred_cov.shape, (8, 8))

        # Update with new measurement (moving right by 5px)
        measurement2 = np.array([105.0, 200.0, 0.5, 80.0], dtype=np.float32)
        updated_mean, updated_cov = self.kf.update(pred_mean, pred_cov, measurement2)

        self.assertEqual(updated_mean.shape, (8,))
        # X-center should update closer to 105.0
        self.assertGreater(updated_mean[0], 100.0)

    def test_gating_distance(self):
        """Test Mahalanobis gating distance calculation."""
        measurement = np.array([100.0, 200.0, 0.5, 80.0], dtype=np.float32)
        mean, covariance = self.kf.initiate(measurement)

        measurements = np.array([
            [100.0, 200.0, 0.5, 80.0],  # Exact match -> low distance
            [500.0, 800.0, 0.5, 80.0],  # Far away -> high distance
        ], dtype=np.float32)

        distances = self.kf.gating_distance(mean, covariance, measurements)
        self.assertEqual(len(distances), 2)
        self.assertLess(distances[0], distances[1])


if __name__ == "__main__":
    unittest.main()
