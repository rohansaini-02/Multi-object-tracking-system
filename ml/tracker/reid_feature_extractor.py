"""
Re-ID Feature Extractor using PyTorch CNN model.
Extracts L2-normalized feature embeddings from bounding box image crops.
"""

from typing import List, Optional, Tuple
import logging
import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T
import torchvision.models as models

from ml.types import BoundingBox, Detection

logger = logging.getLogger(__name__)


class Net(nn.Module):
    """Lightweight Re-ID Embedding Network based on ResNet-18."""

    def __init__(self, reid_dim: int = 128, pretrained: bool = True):
        super(Net, self).__init__()
        # Use ResNet18 as backbone
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        resnet = models.resnet18(weights=weights)
        
        # Remove final FC layer
        self.backbone = nn.Sequential(*list(resnet.children())[:-1])
        self.fc = nn.Linear(512, reid_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        feat = feat.view(feat.size(0), -1)
        out = self.fc(feat)
        # L2 normalization
        norm = out.norm(p=2, dim=1, keepdim=True).clamp(min=1e-12)
        out = out / norm
        return out


class ReidFeatureExtractor:
    """Extracts normalized appearance feature embeddings from bounding box crops."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        feature_dim: int = 128,
        input_size: Tuple[int, int] = (128, 64),  # (height, width)
        device: Optional[str] = None,
    ):
        """
        Args:
            model_path: Path to custom fine-tuned PyTorch weights (.pth). If None or missing, uses ImageNet pretrained ResNet18.
            feature_dim: Output dimension of feature vector (default: 128).
            input_size: Target (height, width) for image crop preprocessing.
            device: 'cuda', 'cpu', or auto.
        """
        self.feature_dim = feature_dim
        self.input_size = input_size
        
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Initialize network architecture
        self.net = Net(reid_dim=feature_dim, pretrained=True)

        # Load weights if custom model provided
        if model_path and os.path.exists(model_path):
            try:
                state_dict = torch.load(model_path, map_location=self.device)
                self.net.load_state_dict(state_dict)
                logger.info("Loaded weights from %s", model_path)
            except Exception as e:
                logger.warning("Failed to load weights from %s: %s", model_path, e)

        self.net.to(self.device)
        self.net.eval()

        # Image preprocessing pipeline (Standard ImageNet normalization)
        self.transform = T.Compose([
            T.ToPILImage(),
            T.Resize(input_size),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def _crop_image(self, frame: np.ndarray, bbox: BoundingBox) -> Optional[np.ndarray]:
        """Crop and validate bounding box region from BGR frame."""
        h, w, _ = frame.shape
        x1 = max(0, int(round(bbox.x1)))
        y1 = max(0, int(round(bbox.y1)))
        x2 = min(w, int(round(bbox.x2)))
        y2 = min(h, int(round(bbox.y2)))

        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        return crop

    @torch.inference_mode()
    def extract(self, frame: np.ndarray, detections: List[Detection]) -> List[Detection]:
        """Extract feature embeddings for all detections in a frame and attach in-place."""
        if not detections:
            return detections

        crops = []
        valid_indices = []

        for idx, det in enumerate(detections):
            crop = self._crop_image(frame, det.bbox)
            if crop is not None:
                try:
                    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    tensor_crop = self.transform(crop_rgb)
                    crops.append(tensor_crop)
                    valid_indices.append(idx)
                except Exception:
                    det.feature = np.zeros(self.feature_dim, dtype=np.float32)
            else:
                det.feature = np.zeros(self.feature_dim, dtype=np.float32)

        if len(crops) > 0:
            try:
                # Process in small mini-batches of 16 to prevent memory spikes
                batch_size = 16
                all_features = []
                for i in range(0, len(crops), batch_size):
                    batch_tensors = torch.stack(crops[i:i + batch_size]).to(self.device)
                    feats = self.net(batch_tensors).cpu().numpy()
                    all_features.append(feats)

                features = np.vstack(all_features)
                for idx, feat in zip(valid_indices, features):
                    detections[idx].feature = feat
            except Exception as e:
                logger.warning("ReID batch feature extraction fallback: %s", e)
                for idx in valid_indices:
                    detections[idx].feature = np.random.randn(self.feature_dim).astype(np.float32)

        return detections
