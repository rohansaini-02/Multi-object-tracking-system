"""
Matching algorithms for DeepSORT (Hungarian assignment, Cosine Distance, IoU Distance, Cascaded Matching).

Production Engineering Notes:
-----------------------------
1. Feature Normalization & Numerical Stability:
   Cosine distance d(u, v) = 1 - dot(u, v) relies on u and v being unit L2-normalized vectors.
   Features are clipped to [0.0, 2.0] distance bounds to prevent floating-point roundoff errors
   (e.g., dot product returning 1.0000001 resulting in negative distance).

2. Hungarian Assignment Gating:
   SciPy's `linear_sum_assignment` finds the global minimal assignment cost. Gated entries
   (distance > max_distance) are assigned large penalty costs during assignment, and post-filtered
   to ensure no gated pair is ever returned in `matches`.

3. DeepSORT Cascade Priority:
   Evaluates tracks in order of `time_since_update` (level 0 to cascade_depth).
   Tracks seen in the previous frame get first assignment priority, preventing older coasting
   tracks with inflated Kalman spatial covariance from stealing detections.
"""

from typing import List, Tuple, Optional, Callable, Any
import numpy as np
from scipy.optimize import linear_sum_assignment

from ml.types import BoundingBox, Detection


def iou(bbox1: BoundingBox, bbox2: BoundingBox) -> float:
    """Calculate Intersection-over-Union (IoU) ratio between two bounding boxes.

    Handles zero-area and non-overlapping box edge cases safely.
    """
    x1 = max(bbox1.x1, bbox2.x1)
    y1 = max(bbox1.y1, bbox2.y1)
    x2 = min(bbox1.x2, bbox2.x2)
    y2 = min(bbox1.y2, bbox2.y2)

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = bbox1.area
    area2 = bbox2.area
    union_area = area1 + area2 - inter_area

    if union_area <= 0.0:
        return 0.0
    return float(inter_area / union_area)


def iou_cost_matrix(
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> np.ndarray:
    """Compute (1 - IoU) distance cost matrix between tracks and detections."""
    if track_indices is None:
        track_indices = list(range(len(tracks)))
    if detection_indices is None:
        detection_indices = list(range(len(detections)))

    cost_matrix = np.ones((len(track_indices), len(detection_indices)), dtype=np.float32)
    if len(track_indices) == 0 or len(detection_indices) == 0:
        return cost_matrix

    for i, trk_idx in enumerate(track_indices):
        trk_bbox = tracks[trk_idx].to_tlwh_bbox()
        for j, det_idx in enumerate(detection_indices):
            det_bbox = detections[det_idx].bbox
            iou_score = iou(trk_bbox, det_bbox)
            cost_matrix[i, j] = 1.0 - iou_score

    return cost_matrix


def cosine_distance_matrix(
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> np.ndarray:
    """Compute minimum Cosine Distance matrix between track feature galleries and detection features.

    Numerical & Edge Case Safeguards:
    ---------------------------------
    - Validates that features are 1D arrays and non-empty.
    - Safe L2 normalization: vector / max(norm, 1e-12).
    - Distance values clipped to range [0.0, 2.0] for numerical stability.
    """
    if track_indices is None:
        track_indices = list(range(len(tracks)))
    if detection_indices is None:
        detection_indices = list(range(len(detections)))

    cost_matrix = np.ones((len(track_indices), len(detection_indices)), dtype=np.float32)
    if len(track_indices) == 0 or len(detection_indices) == 0:
        return cost_matrix

    # Process and normalize detection feature vectors
    det_feat_list = []
    for det_idx in detection_indices:
        feat = detections[det_idx].feature
        if feat is not None and isinstance(feat, np.ndarray) and feat.size > 0:
            norm = np.linalg.norm(feat)
            norm_feat = feat / max(norm, 1e-12)
            det_feat_list.append(norm_feat)
        else:
            det_feat_list.append(None)

    for i, trk_idx in enumerate(track_indices):
        track_gallery = tracks[trk_idx].features
        if not track_gallery:
            cost_matrix[i, :] = 1.0
            continue

        # Filter valid gallery features for current track
        valid_gallery = []
        for feat in track_gallery:
            if feat is not None and isinstance(feat, np.ndarray) and feat.size > 0:
                norm = np.linalg.norm(feat)
                valid_gallery.append(feat / max(norm, 1e-12))

        if not valid_gallery:
            cost_matrix[i, :] = 1.0
            continue

        gallery_mat = np.array(valid_gallery, dtype=np.float32)

        for j, det_feat in enumerate(det_feat_list):
            if det_feat is None or det_feat.shape != gallery_mat.shape[1:]:
                cost_matrix[i, j] = 1.0
                continue

            # Dot product for unit normalized vectors = Cosine Similarity
            dot_prods = np.dot(gallery_mat, det_feat)
            # Distance = 1.0 - Cosine Similarity, clipped for numerical stability
            dists = np.clip(1.0 - dot_prods, 0.0, 2.0)
            cost_matrix[i, j] = float(np.min(dists))

    return cost_matrix


def min_cost_matching(
    distance_metric_fn: Callable,
    max_distance: float,
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Solve linear assignment problem using the Hungarian algorithm (linear_sum_assignment).

    Applies large penalty cost (1e5) to gated elements before running linear assignment,
    and strictly validates matched costs post-assignment.

    Returns:
        (matches, unmatched_tracks, unmatched_detections):
          matches: List of tuples (track_index, detection_index)
          unmatched_tracks: List of unassigned track indices
          unmatched_detections: List of unassigned detection indices
    """
    if track_indices is None:
        track_indices = list(range(len(tracks)))
    if detection_indices is None:
        detection_indices = list(range(len(detections)))

    if len(track_indices) == 0 or len(detection_indices) == 0:
        return [], list(track_indices), list(detection_indices)

    # Compute raw cost matrix
    cost_matrix = distance_metric_fn(tracks, detections, track_indices, detection_indices)

    # Copy matrix and apply large penalty to gated pairs exceeding max_distance
    gated_cost_matrix = cost_matrix.copy()
    gated_cost_matrix[gated_cost_matrix > max_distance] = max_distance + 1e5

    # Run Hungarian algorithm assignment
    row_indices, col_indices = linear_sum_assignment(gated_cost_matrix)

    matches = []
    unmatched_tracks = list(track_indices)
    unmatched_detections = list(detection_indices)

    for row, col in zip(row_indices, col_indices):
        trk_idx = track_indices[row]
        det_idx = detection_indices[col]

        # Reject assignment if distance cost exceeds threshold gating limit
        if cost_matrix[row, col] > max_distance:
            continue

        matches.append((trk_idx, det_idx))
        if trk_idx in unmatched_tracks:
            unmatched_tracks.remove(trk_idx)
        if det_idx in unmatched_detections:
            unmatched_detections.remove(det_idx)

    return matches, unmatched_tracks, unmatched_detections


def matching_cascade(
    distance_metric_fn: Callable,
    max_distance: float,
    cascade_depth: int,
    tracks: List[Any],
    detections: List[Detection],
    track_indices: Optional[List[int]] = None,
    detection_indices: Optional[List[int]] = None,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Cascaded matching solver prioritizing frequently updated tracks.

    Iterates level 0 to cascade_depth-1 (level 0 = updated 1 frame ago).
    Unmatched detections cascade to subsequent levels.
    """
    if track_indices is None:
        track_indices = list(range(len(tracks)))
    if detection_indices is None:
        detection_indices = list(range(len(detections)))

    unmatched_detections = list(detection_indices)
    matches = []

    for level in range(cascade_depth):
        if len(unmatched_detections) == 0:
            break

        # Select tracks updated level+1 frames ago
        level_track_indices = [
            k for k in track_indices if tracks[k].time_since_update == level + 1
        ]
        if len(level_track_indices) == 0:
            continue

        level_matches, _, unmatched_detections = min_cost_matching(
            distance_metric_fn,
            max_distance,
            tracks,
            detections,
            level_track_indices,
            unmatched_detections,
        )
        matches.extend(level_matches)

    unmatched_tracks = [
        k for k in track_indices if k not in [m[0] for m in matches]
    ]
    return matches, unmatched_tracks, unmatched_detections
