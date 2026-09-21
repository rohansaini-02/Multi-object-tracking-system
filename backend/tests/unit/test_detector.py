"""
Unit Tests for YOLOv8 Detector & Data Loaders (Week 2 Milestone).
"""

import os
import unittest
import numpy as np

from ml.types import BoundingBox, Detection
from backend.app.ml.detector import YOLOv8Detector


class TestBoundingBoxAndDetector(unittest.TestCase):
    def test_bounding_box_conversions(self):
        """Test BoundingBox coordinate conversions (TLWH, XYAH, XYXY)."""
        bbox = BoundingBox(x1=10.0, y1=20.0, x2=110.0, y2=220.0)
        self.assertEqual(bbox.width, 100.0)
        self.assertEqual(bbox.height, 200.0)
        self.assertEqual(bbox.area, 20000.0)
        self.assertEqual(bbox.aspect_ratio, 0.5)

        # TLWH conversion: (x1, y1, width, height)
        tlwh = bbox.to_tlwh()
        self.assertEqual(tlwh, (10.0, 20.0, 100.0, 200.0))

        # Reconstruct from TLWH
        bbox_from_tlwh = BoundingBox.from_tlwh(10.0, 20.0, 100.0, 200.0)
        self.assertEqual(bbox_from_tlwh.x1, 10.0)
        self.assertEqual(bbox_from_tlwh.x2, 110.0)

        # XYAH conversion: (cx, cy, aspect_ratio, height)
        cx, cy, a, h = bbox.to_xyah()
        self.assertEqual(cx, 60.0)
        self.assertEqual(cy, 120.0)
        self.assertEqual(a, 0.5)
        self.assertEqual(h, 200.0)

        # Reconstruct from XYAH
        bbox_from_xyah = BoundingBox.from_xyah(cx, cy, a, h)
        self.assertAlmostEqual(bbox_from_xyah.x1, 10.0)
        self.assertAlmostEqual(bbox_from_xyah.y1, 20.0)
        self.assertAlmostEqual(bbox_from_xyah.x2, 110.0)
        self.assertAlmostEqual(bbox_from_xyah.y2, 220.0)

    def test_detection_filtering(self):
        """Test confidence and class ID filtering on Detection objects."""
        raw_detections = [
            Detection(bbox=BoundingBox(0, 0, 50, 50), confidence=0.8, class_id=0),  # Person, high conf
            Detection(bbox=BoundingBox(10, 10, 60, 60), confidence=0.3, class_id=0), # Person, low conf
            Detection(bbox=BoundingBox(20, 20, 70, 70), confidence=0.9, class_id=2), # Car, high conf
        ]

        # Filter by conf >= 0.5 and class_id == 0 (Person)
        filtered = [
            d for d in raw_detections
            if d.confidence >= 0.5 and d.class_id == 0
        ]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].confidence, 0.8)
        self.assertEqual(filtered[0].class_id, 0)


if __name__ == "__main__":
    unittest.main()
