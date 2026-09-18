"""
Hungarian Matching Cascade & Cost Matrices Module for Backend Pipeline (Week 4 Milestone).
"""

from typing import List, Tuple, Optional, Callable, Any
import numpy as np

from ml.tracker.matching import (
    iou,
    iou_cost_matrix,
    cosine_distance_matrix,
    min_cost_matching as standalone_min_cost_matching,
    matching_cascade as standalone_matching_cascade,
)
from ml.types import Detection


def compute_cosine_distance_matrix(
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> np.ndarray:
    """Compute minimum Cosine Distance matrix between tracks' feature galleries and detection features."""
    return cosine_distance_matrix(tracks, detections, track_indices, detection_indices)


def compute_iou_cost_matrix(
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> np.ndarray:
    """Compute (1 - IoU) cost matrix between tracks' bounding boxes and detection boxes."""
    return iou_cost_matrix(tracks, detections, track_indices, detection_indices)


def solve_hungarian_matching(
    distance_metric_fn: Callable,
    max_distance: float,
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Solve linear sum assignment problem using the Hungarian algorithm."""
    return standalone_min_cost_matching(
        distance_metric_fn,
        max_distance,
        tracks,
        detections,
        track_indices,
        detection_indices,
    )


def solve_matching_cascade(
    distance_metric_fn: Callable,
    max_distance: float,
    cascade_depth: int,
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Solve multi-level cascaded matching prioritising frequently updated tracks."""
    return standalone_matching_cascade(
        distance_metric_fn,
        max_distance,
        cascade_depth,
        tracks,
        detections,
        track_indices,
        detection_indices,
    )
