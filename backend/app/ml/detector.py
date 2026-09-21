"""
YOLOv8 Detector Integration Module for Backend ML Pipeline (Week 2 Milestone).
Wraps Ultralytics YOLOv8 for object detection with confidence & class filtering.
"""

from typing import List, Optional
import numpy as np

from ml.detectors.yolo_detector import YOLOv8Detector as StandaloneYOLOv8Detector
from ml.types import BoundingBox, Detection


class YOLOv8Detector:
    """YOLOv8 object detector adapter for backend processing."""

    def __init__(
        self,
        model_path: str = "weights/yolov8m.pt",
        conf_threshold: float = 0.25,
        target_classes: Optional[List[int]] = None,
        device: Optional[str] = None,
    ):
        """
        Args:
            model_path: Path to model weights (e.g. 'weights/yolov8m.pt').
            conf_threshold: Minimum confidence score threshold [0.0, 1.0].
            target_classes: List of class IDs to retain (e.g. [0] for person).
            device: 'cuda', 'cpu', or auto.
        """
        self.detector = StandaloneYOLOv8Detector(
            model_path=model_path,
            conf_threshold=conf_threshold,
            target_classes=target_classes,
            device=device,
        )

    def warmup(self) -> None:
        """Pre-load model weights into memory/GPU."""
        self.detector.warmup()

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Detect objects in a single BGR frame array.

        Args:
            frame: BGR numpy image array (H, W, 3).

        Returns:
            List of Detection objects containing BoundingBox, confidence, and class_id.
        """
        return self.detector.detect(frame)
