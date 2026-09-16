"""
Visualization and file output utilities for tracking results.
"""

import os
from typing import Dict, List, Tuple
import cv2
import numpy as np

from ml.types import TrackOutput, FrameTrackingResult


def get_color_for_id(track_id: int) -> Tuple[int, int, int]:
    """Generate a distinct, consistent BGR color for a given track ID using golden ratio coloring."""
    golden_ratio = 0.618033988749895
    hue = (track_id * golden_ratio) % 1.0
    saturation = 0.85
    value = 0.95
    
    # Convert HSV (0-1) to BGR (0-255)
    hsv = np.uint8([[[hue * 180, saturation * 255, value * 255]]])
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))


def draw_tracks_on_frame(
    frame: np.ndarray,
    tracks: List[TrackOutput],
    show_confidence: bool = True,
    line_thickness: int = 2,
    font_scale: float = 0.6,
) -> np.ndarray:
    """Draw bounding boxes and ID text labels on a frame array.
    
    Args:
        frame: BGR image array (H, W, 3). Modified in-place or returned.
        tracks: List of active track outputs.
        show_confidence: Whether to append confidence score to label.
        line_thickness: Box stroke width.
        font_scale: Scale factor for label text.
        
    Returns:
        Annotated BGR frame array.
    """
    annotated = frame.copy()

    for trk in tracks:
        bbox = trk.bbox
        x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)
        color = get_color_for_id(trk.track_id)

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, line_thickness)

        # Prepare label string
        if show_confidence:
            label = f"ID:{trk.track_id} ({trk.confidence:.2f})"
        else:
            label = f"ID:{trk.track_id}"

        # Draw filled text background box for high readability
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        bg_y1 = max(0, y1 - text_h - baseline - 4)
        bg_y2 = y1
        cv2.rectangle(
            annotated,
            (x1, bg_y1),
            (x1 + text_w + 6, bg_y2),
            color,
            -1,  # Filled
        )

        # Draw text label in white/black depending on color brightness
        brightness = 0.299 * color[2] + 0.587 * color[1] + 0.114 * color[0]
        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
        
        cv2.putText(
            annotated,
            label,
            (x1 + 3, max(text_h + 2, y1 - baseline - 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            text_color,
            1,
            cv2.LINE_AA,
        )

    return annotated


def export_mot_results(results: List[FrameTrackingResult], output_path: str) -> None:
    """Save tracking results to disk in MOT Challenge format.
    
    Format: frame_id, track_id, top, left, width, height, conf, -1, -1, -1
    (1-indexed frame numbers)
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        for res in results:
            frame_idx = res.frame_idx
            for trk in res.tracks:
                top, left, width, height = trk.bbox.to_tlwh()
                # MOT format: frame, id, top, left, width, height, conf, -1, -1, -1
                line = f"{frame_idx},{trk.track_id},{top:.2f},{left:.2f},{width:.2f},{height:.2f},{trk.confidence:.4f},-1,-1,-1\n"
                f.write(line)
