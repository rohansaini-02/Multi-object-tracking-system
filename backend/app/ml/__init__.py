"""
Backend ML Module Package (Week 2 Detector & Data Loaders).
"""

from backend.app.ml.detector import YOLOv8Detector
from backend.app.ml.data_loader import VideoDataLoader, MOT17SequenceDataLoader

__all__ = ["YOLOv8Detector", "VideoDataLoader", "MOT17SequenceDataLoader"]
