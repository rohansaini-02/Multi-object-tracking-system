"""
Unit Test Suite for Matching Algorithms (IoU, Cosine Distance, Hungarian Assignment, Cascade).
"""

import unittest
import numpy as np

from ml.types import BoundingBox, Detection
from ml.tracker.matching import (
    iou,
    iou_cost_matrix,
    cosine_distance_matrix,
    min_cost_matching,
    matching_cascade,
)


class MockTrack:
    """Mock Track object for testing matching algorithms in isolation."""

    def __init__(self, bbox: BoundingBox, time_since_update: int = 1, features=None):
        self.bbox = bbox
        self.time_since_update = time_since_update
        self.features = features if features is not None else []

    def to_tlwh_bbox(self) -> BoundingBox:
        return self.bbox


class TestMatchingAlgorithms(unittest.TestCase):
    def test_iou_calculation(self):
        """Test IoU calculation for identical, partial, and disjoint bounding boxes."""
        box1 = BoundingBox(0.0, 0.0, 10.0, 10.0)  # Area 100
        box2 = BoundingBox(0.0, 0.0, 10.0, 10.0)  # Identical -> IoU 1.0
        box3 = BoundingBox(5.0, 0.0, 15.0, 10.0)  # Overlap 50, union 150 -> IoU 0.3333
        box4 = BoundingBox(20.0, 20.0, 30.0, 30.0) # Disjoint -> IoU 0.0

        self.assertAlmostEqual(iou(box1, box2), 1.0)
        self.assertAlmostEqual(iou(box1, box3), 50.0 / 150.0)
        self.assertEqual(iou(box1, box4), 0.0)

    def test_iou_cost_matrix(self):
        """Test 1 - IoU cost matrix generation."""
        tracks = [MockTrack(BoundingBox(0.0, 0.0, 10.0, 10.0))]
        detections = [
            Detection(bbox=BoundingBox(0.0, 0.0, 10.0, 10.0), confidence=0.9),  # IoU 1.0 -> Cost 0.0
            Detection(bbox=BoundingBox(20.0, 20.0, 30.0, 30.0), confidence=0.8), # IoU 0.0 -> Cost 1.0
        ]

        cost_mat = iou_cost_matrix(tracks, detections)
        self.assertEqual(cost_mat.shape, (1, 2))
        self.assertAlmostEqual(cost_mat[0, 0], 0.0)
        self.assertAlmostEqual(cost_mat[0, 1], 1.0)

    def test_cosine_distance_matrix_and_feature_normalization(self):
        """Test Cosine distance matrix computation with normalized vectors and empty edge cases."""
        feat_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)  # Unit vector X
        feat_b = np.array([1.0, 0.0, 0.0], dtype=np.float32)  # Identical -> distance 0.0
        feat_c = np.array([0.0, 1.0, 0.0], dtype=np.float32)  # Orthogonal -> distance 1.0

        tracks = [
            MockTrack(bbox=BoundingBox(0, 0, 10, 10), features=[feat_a]),
            MockTrack(bbox=BoundingBox(0, 0, 10, 10), features=[]),  # Empty gallery
        ]
        detections = [
            Detection(bbox=BoundingBox(0, 0, 10, 10), confidence=0.9, feature=feat_b),
            Detection(bbox=BoundingBox(0, 0, 10, 10), confidence=0.9, feature=feat_c),
            Detection(bbox=BoundingBox(0, 0, 10, 10), confidence=0.9, feature=None),  # None feature
        ]

        cost_mat = cosine_distance_matrix(tracks, detections)
        self.assertEqual(cost_mat.shape, (2, 3))

        # Track 0 vs Det 0 (identical feature) -> distance ~ 0.0
        self.assertAlmostEqual(cost_mat[0, 0], 0.0, places=5)
        # Track 0 vs Det 1 (orthogonal feature) -> distance ~ 1.0
        self.assertAlmostEqual(cost_mat[0, 1], 1.0, places=5)
        # Track 0 vs Det 2 (None feature) -> fallback distance 1.0
        self.assertEqual(cost_mat[0, 2], 1.0)
        # Track 1 (Empty gallery) -> fallback distance 1.0 across all
        self.assertEqual(cost_mat[1, 0], 1.0)

    def test_min_cost_matching_and_gating_cutoff(self):
        """Test Hungarian assignment algorithm and max_distance gating threshold cutoff."""
        tracks = [
            MockTrack(BoundingBox(0.0, 0.0, 10.0, 10.0)),
            MockTrack(BoundingBox(100.0, 100.0, 110.0, 110.0)),
        ]
        detections = [
            Detection(bbox=BoundingBox(0.0, 0.0, 10.0, 10.0), confidence=0.9),  # Matches track 0
            Detection(bbox=BoundingBox(500.0, 500.0, 510.0, 510.0), confidence=0.8), # Far -> Gated out
        ]

        # Match with max_distance threshold 0.5 (1 - IoU)
        matches, unmatched_tracks, unmatched_detections = min_cost_matching(
            iou_cost_matrix,
            max_distance=0.5,
            tracks=tracks,
            detections=detections,
        )

        # Track 0 matches Det 0
        self.assertEqual(matches, [(0, 0)])
        # Track 1 is unmatched
        self.assertEqual(unmatched_tracks, [1])
        # Det 1 is unmatched (gated out by max_distance threshold)
        self.assertEqual(unmatched_detections, [1])

    def test_matching_cascade_priority(self):
        """Test matching cascade prioritizing recently seen tracks (level 0) over older tracks (level 1)."""
        # Track 0 (updated 1 frame ago), Track 1 (updated 2 frames ago)
        # Both tracks have identical bounding boxes
        box = BoundingBox(0.0, 0.0, 10.0, 10.0)
        tracks = [
            MockTrack(box, time_since_update=1),
            MockTrack(box, time_since_update=2),
        ]
        detections = [
            Detection(bbox=box, confidence=0.9),  # Single detection
        ]

        matches, unmatched_tracks, unmatched_detections = matching_cascade(
            iou_cost_matrix,
            max_distance=0.5,
            cascade_depth=3,
            tracks=tracks,
            detections=detections,
        )

        # Track 0 (level 0, time_since_update=1) must win the match
        self.assertEqual(matches, [(0, 0)])
        self.assertEqual(unmatched_tracks, [1])
        self.assertEqual(unmatched_detections, [])


if __name__ == "__main__":
    unittest.main()
