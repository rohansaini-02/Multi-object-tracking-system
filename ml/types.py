"""
Core data types for the Multi-Object Tracking ML module.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import numpy as np


class TrackState(Enum):
    """Lifecycle states for a tracked object in DeepSORT."""
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    DELETED = "deleted"


@dataclass
class BoundingBox:
    """Bounding box representation in [x1, y1, x2, y2] pixel coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def aspect_ratio(self) -> float:
        h = self.height
        return self.width / h if h > 0 else 0.0

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_tlwh(self) -> Tuple[float, float, float, float]:
        """Convert to [top-left-x, top-left-y, width, height]."""
        return (self.x1, self.y1, self.width, self.height)

    def to_xyah(self) -> Tuple[float, float, float, float]:
        """Convert to [center-x, center-y, aspect-ratio, height]."""
        cx = self.x1 + self.width / 2.0
        cy = self.y1 + self.height / 2.0
        return (cx, cy, self.aspect_ratio, self.height)

    def to_xyxy(self) -> Tuple[float, float, float, float]:
        """Convert to [x1, y1, x2, y2]."""
        return (self.x1, self.y1, self.x2, self.y2)

    @classmethod
    def from_tlwh(cls, x1: float, y1: float, width: float, height: float) -> "BoundingBox":
        return cls(x1=x1, y1=y1, x2=x1 + width, y2=y1 + height)

    @classmethod
    def from_xyah(cls, cx: float, cy: float, aspect_ratio: float, height: float) -> "BoundingBox":
        width = aspect_ratio * height
        x1 = cx - width / 2.0
        y1 = cy - height / 2.0
        return cls(x1=x1, y1=y1, x2=x1 + width, y2=y1 + height)


@dataclass
class Detection:
    """Object detection output for a single frame."""
    bbox: BoundingBox
    confidence: float
    class_id: int = 0
    feature: Optional[np.ndarray] = None  # Re-ID feature vector (e.g. 128-dim or 512-dim)


@dataclass
class TrackOutput:
    """Track output representation for export/visualization."""
    track_id: int
    bbox: BoundingBox
    confidence: float
    class_id: int = 0
    state: TrackState = TrackState.CONFIRMED


@dataclass
class FrameTrackingResult:
    """Tracking results for a single frame."""
    frame_idx: int
    tracks: List[TrackOutput] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Summary result of a full video tracking pipeline run."""
    total_frames: int
    processed_frames: int
    total_tracks: int
    fps: float
    output_video_path: Optional[str] = None
    output_mot_path: Optional[str] = None
