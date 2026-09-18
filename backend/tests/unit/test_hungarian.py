"""
Unit Tests for Hungarian Matching Cascade and Distance Matrices (Week 4 Milestone).
"""

import unittest
import numpy as np

from ml.types import BoundingBox, Detection
from backend.app.ml.hungarian import (
    compute_cosine_distance_matrix,
    compute_iou_cost_matrix,
    solve_hungarian_matching,
    solve_matching_cascade,
)


class MockTrack:
    def __init__(self, bbox: BoundingBox, time_since_update: int = 1, features=None):
        self.bbox = bbox
        self.time_since_update = time_since_update
        self.features = features if features is not None else []

    def to_tlwh_bbox(self) -> BoundingBox:
        return self.bbox


class TestHungarianMatching(unittest.TestCase):
    def test_cosine_distance_computation(self):
        """Test Cosine distance matrix computation."""
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        tracks = [MockTrack(bbox=BoundingBox(0, 0, 10, 10), features=[v1])]
        detections = [
            Detection(bbox=BoundingBox(0, 0, 10, 10), confidence=0.9, feature=v2),
            Detection(bbox=BoundingBox(0, 0, 10, 10), confidence=0.9, feature=v3),
        ]

        cost_mat = compute_cosine_distance_matrix(tracks, detections)
        self.assertEqual(cost_mat.shape, (1, 2))
        self.assertAlmostEqual(cost_mat[0, 0], 0.0, places=5)
        self.assertAlmostEqual(cost_mat[0, 1], 1.0, places=5)

    def test_hungarian_assignment_and_gating(self):
        """Test Hungarian linear assignment with max_distance cutoff."""
        tracks = [
            MockTrack(BoundingBox(0.0, 0.0, 10.0, 10.0)),
            MockTrack(BoundingBox(100.0, 100.0, 110.0, 110.0)),
        ]
        detections = [
            Detection(bbox=BoundingBox(0.0, 0.0, 10.0, 10.0), confidence=0.9),  # Matches track 0
            Detection(bbox=BoundingBox(500.0, 500.0, 510.0, 510.0), confidence=0.8), # Gated out
        ]

        matches, unmatched_tracks, unmatched_detections = solve_hungarian_matching(
            compute_iou_cost_matrix,
            max_distance=0.5,
            tracks=tracks,
            detections=detections,
        )

        self.assertEqual(matches, [(0, 0)])
        self.assertEqual(unmatched_tracks, [1])
        self.assertEqual(unmatched_detections, [1])

    def test_matching_cascade_priority(self):
        """Test matching cascade prioritises younger tracks (time_since_update=1 over time_since_update=2)."""
        box = BoundingBox(0.0, 0.0, 10.0, 10.0)
        tracks = [
            MockTrack(box, time_since_update=1),
            MockTrack(box, time_since_update=2),
        ]
        detections = [Detection(bbox=box, confidence=0.9)]

        matches, unmatched_tracks, unmatched_detections = solve_matching_cascade(
            compute_iou_cost_matrix,
            max_distance=0.5,
            cascade_depth=3,
            tracks=tracks,
            detections=detections,
        )

        self.assertEqual(matches, [(0, 0)])
        self.assertEqual(unmatched_tracks, [1])


if __name__ == "__main__":
    unittest.main()
