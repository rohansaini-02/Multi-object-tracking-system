"""
Abstract Base Class for Object Detectors (Strategy Pattern).
"""

from abc import ABC, abstractmethod
from typing import List
import numpy as np

from ml.types import Detection


class BaseDetector(ABC):
    """Abstract base class for swappable detection backends."""

    @abstractmethod
    def warmup(self) -> None:
        """Pre-loads model weights into memory/GPU. Called once at startup."""
        pass

    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Detect objects in a single BGR image array.
        
        Args:
            frame: BGR numpy image array (H, W, 3).
            
        Returns:
            List of Detection objects with bounding box and confidence score.
        """
        pass
