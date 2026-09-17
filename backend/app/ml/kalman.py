"""
Kalman Filter Motion Model for Bounding Box State Estimation (Week 3 Milestone).

State vector (8-dim): [cx, cy, a, h, vcx, vcy, va, vh]
  cx, cy : Bounding box center coordinates
  a      : Bounding box aspect ratio (width / height)
  h      : Bounding box height
  vcx... : Velocities of corresponding state variables

Measurement vector (4-dim): [cx, cy, a, h]
"""

from typing import Tuple
import numpy as np
import scipy.linalg


class KalmanFilter:
    """An 8-dimensional Kalman filter for tracking bounding boxes in image space.
    
    Uses constant velocity motion model and state-dependent noise covariances
    scaled by bounding box height to handle perspective scale changes.
    """

    def __init__(self):
        ndim, dt = 4, 1.0

        # State transition matrix F (8x8)
        self._motion_mat = np.eye(2 * ndim, 2 * ndim, dtype=np.float32)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt

        # Measurement projection matrix H (4x8)
        self._update_mat = np.eye(ndim, 2 * ndim, dtype=np.float32)

        # Motion and measurement uncertainty factors
        self._std_weight_position = 1.0 / 20.0
        self._std_weight_velocity = 1.0 / 160.0

    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Initialize state distribution (mean and covariance) from unassociated detection.

        Args:
            measurement: 4-dim array [cx, cy, a, h].

        Returns:
            (mean, covariance): 8-dim state mean vector and 8x8 covariance matrix.
        """
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Run Kalman filter prediction step to estimate state at current timestep.

        Args:
            mean: Current 8-dim state mean.
            covariance: Current 8x8 state covariance.

        Returns:
            (mean, covariance): Predicted 8-dim state mean and 8x8 covariance.
        """
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))

        predicted_mean = np.dot(self._motion_mat, mean)
        predicted_covariance = (
            np.linalg.multi_dot((self._motion_mat, covariance, self._motion_mat.T))
            + motion_cov
        )
        return predicted_mean, predicted_covariance

    def project(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Project 8-dim state distribution to 4-dim measurement space [cx, cy, a, h]."""
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))

        projected_mean = np.dot(self._update_mat, mean)
        projected_covariance = (
            np.linalg.multi_dot((self._update_mat, covariance, self._update_mat.T))
            + innovation_cov
        )
        return projected_mean, projected_covariance

    def update(
        self, mean: np.ndarray, covariance: np.ndarray, measurement: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Incorporate new detection measurement to update state distribution.

        Args:
            mean: Predicted 8-dim state mean.
            covariance: Predicted 8x8 state covariance.
            measurement: 4-dim measurement vector [cx, cy, a, h].

        Returns:
            (mean, covariance): Updated 8-dim state mean and 8x8 covariance.
        """
        projected_mean, projected_cov = self.project(mean, covariance)

        chol_factor, lower = scipy.linalg.cho_factor(
            projected_cov, lower=True, check_finite=False
        )
        kalman_gain = scipy.linalg.cho_solve(
            (chol_factor, lower),
            np.dot(covariance, self._update_mat.T).T,
            check_finite=False,
        ).T

        innovation = measurement - projected_mean
        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_covariance = covariance - np.linalg.multi_dot(
            (kalman_gain, projected_cov, kalman_gain.T)
        )
        return new_mean, new_covariance

    def gating_distance(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        measurements: np.ndarray,
        only_position: bool = False,
    ) -> np.ndarray:
        """Compute squared Mahalanobis distance between predicted state and measurements."""
        mean, covariance = self.project(mean, covariance)
        if only_position:
            mean, covariance = mean[:2], covariance[:2, :2]
            measurements = measurements[:, :2]

        cholesky_factor = np.linalg.cholesky(covariance)
        d = measurements - mean
        z = scipy.linalg.solve_triangular(
            cholesky_factor, d.T, lower=True, check_finite=False
        )
        return np.sum(z * z, axis=0)
