"""
Unit Tests for Re-ID Feature Extractor (Week 4 Milestone).
"""

import unittest
import numpy as np

from ml.types import BoundingBox, Detection
from backend.app.ml.reid import ReidFeatureExtractor


class TestReidFeatureExtractor(unittest.TestCase):
    def setUp(self):
        # Instantiate extractor in CPU mode for fast unit testing
        self.extractor = ReidFeatureExtractor(device="cpu")

    def test_feature_extraction_and_l2_normalization(self):
        """Test feature extraction on a synthetic image frame and verify L2 normalization."""
        # Create a synthetic 100x100 BGR image array
        frame = np.uint8(np.random.randint(0, 255, (100, 100, 3)))
        detections = [
            Detection(bbox=BoundingBox(10.0, 10.0, 60.0, 60.0), confidence=0.9),
            Detection(bbox=BoundingBox(20.0, 20.0, 70.0, 70.0), confidence=0.85),
        ]

        extracted_detections = self.extractor.extract(frame, detections)
        self.assertEqual(len(extracted_detections), 2)

        for det in extracted_detections:
            self.assertIsNotNone(det.feature)
            self.assertEqual(det.feature.shape, (128,))
            # Verify feature is unit L2-normalized: ||v||_2 = 1.0
            norm = float(np.linalg.norm(det.feature))
            self.assertAlmostEqual(norm, 1.0, places=5)

    def test_invalid_crop_handling(self):
        """Test handling of out-of-bounds or zero-area bounding box crops."""
        frame = np.uint8(np.random.randint(0, 255, (100, 100, 3)))
        detections = [
            Detection(bbox=BoundingBox(-50.0, -50.0, -10.0, -10.0), confidence=0.5), # Out of bounds
        ]

        extracted = self.extractor.extract(frame, detections)
        self.assertEqual(len(extracted), 1)
        # Should fallback to zero vector feature
        np.testing.assert_allclose(extracted[0].feature, np.zeros(128, dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
