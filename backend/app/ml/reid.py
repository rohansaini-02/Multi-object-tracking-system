"""
Re-ID Appearance Feature Extractor Module for Backend Pipeline (Week 4 Milestone).

Extracts L2-normalized 128-dimensional appearance feature embeddings from bounding box image patches.
"""

from typing import List, Optional, Tuple
import logging
import numpy as np

from ml.tracker.reid_feature_extractor import ReidFeatureExtractor as StandaloneReidExtractor
from ml.types import BoundingBox, Detection

logger = logging.getLogger(__name__)


class ReidFeatureExtractor:
    """Appearance feature extractor adapter for backend tracking jobs."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        feature_dim: int = 128,
        input_size: Tuple[int, int] = (128, 64),
        device: Optional[str] = None,
    ):
        """
        Args:
            model_path: Optional path to custom fine-tuned PyTorch weights file (.pth).
            feature_dim: Output dimension of embedding vector (default: 128).
            input_size: Target (height, width) for resizing bounding box crops.
            device: 'cuda', 'cpu', or auto.
        """
        self.extractor = StandaloneReidExtractor(
            model_path=model_path,
            feature_dim=feature_dim,
            input_size=input_size,
            device=device,
        )

    def extract(self, frame: np.ndarray, detections: List[Detection]) -> List[Detection]:
        """Extract L2-normalized feature vectors for bounding box crops in frame.

        Args:
            frame: BGR numpy image array (H, W, 3).
            detections: List of Detection objects.

        Returns:
            Updated list of Detection objects with `.feature` attribute populated.
        """
        return self.extractor.extract(frame, detections)
