"""
YOLOv8 Object Detector Implementation using Ultralytics.
"""

from typing import List, Optional
import numpy as np

from ml.detectors.base import BaseDetector
from ml.types import BoundingBox, Detection


class YOLOv8Detector(BaseDetector):
    """YOLOv8 object detector implementation using Ultralytics."""

    def __init__(
        self,
        model_path: str = "yolov8m.pt",
        conf_threshold: float = 0.5,
        target_classes: Optional[List[int]] = None,
        device: Optional[str] = None,
    ):
        """
        Args:
            model_path: Path to model weights (e.g. 'yolov8m.pt' or custom weights).
            conf_threshold: Minimum confidence threshold for detections.
            target_classes: Class IDs to detect (e.g. [0] for person). If None, keeps all classes.
            device: 'cuda', 'cpu', or None for automatic selection.
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.target_classes = target_classes  # If None, YOLO will detect all COCO classes
        self.device = device
        self.model = None

    def warmup(self) -> None:
        """Load YOLO model into memory."""
        if self.model is None:
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
            except ImportError:
                raise ImportError(
                    "Ultralytics is required for YOLOv8Detector. Please install via 'pip install ultralytics'."
                )

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Detect objects in a single frame.
        
        Args:
            frame: BGR numpy image array (H, W, 3).
            
        Returns:
            List of Detection objects.
        """
        if self.model is None:
            self.warmup()

        results = self.model(
            frame,
            conf=self.conf_threshold,
            classes=self.target_classes,
            device=self.device,
            verbose=False,
        )

        detections: List[Detection] = []
        if len(results) == 0:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for box in boxes:
            # xyxy format: [x1, y1, x2, y2]
            coords = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())

            bbox = BoundingBox(
                x1=float(coords[0]),
                y1=float(coords[1]),
                x2=float(coords[2]),
                y2=float(coords[3]),
            )
            detections.append(Detection(bbox=bbox, confidence=conf, class_id=cls_id))

        return detections
