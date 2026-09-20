"""
MOT17 Person Crop Dataset for Re-ID Model Fine-Tuning.
Extracts bounding box image crops of pedestrians from MOT17 ground truth annotations.
"""

from typing import List, Tuple, Optional
import os
import cv2
import torch
from torch.utils.data import Dataset
import torchvision.transforms as T


class MOT17CropDataset(Dataset):
    """Dataset of cropped pedestrian images from MOT17 sequences for Re-ID training."""

    def __init__(
        self,
        mot17_base_dir: str = "data/mot17",
        sequences: Optional[List[str]] = None,
        crop_size: Tuple[int, int] = (128, 64),  # (H, W)
        min_height: int = 40,
        min_visibility: float = 0.3,
        transform: Optional[T.Compose] = None,
    ):
        """
        Args:
            mot17_base_dir: Path to MOT17 root directory.
            sequences: List of sequence names to include (e.g. ['MOT17-04-FRCNN', 'MOT17-10-FRCNN']).
            crop_size: Target (height, width) for resized crops.
            min_height: Minimum crop height in pixels to include.
            min_visibility: Minimum visibility ratio in ground truth annotations (0.0 to 1.0).
            transform: PyTorch vision transformations.
        """
        self.mot17_base_dir = mot17_base_dir
        self.crop_size = crop_size
        self.min_height = min_height
        self.min_visibility = min_visibility

        if sequences is None:
            # Default training split sequences
            sequences = ["MOT17-04-FRCNN", "MOT17-10-FRCNN", "MOT17-11-FRCNN", "MOT17-13-FRCNN"]
        self.sequences = sequences

        if transform is None:
            self.transform = T.Compose([
                T.ToPILImage(),
                T.Resize(crop_size),
                T.RandomHorizontalFlip(p=0.5),
                T.ColorJitter(brightness=0.2, contrast=0.2),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        else:
            self.transform = transform

        self.samples: List[Tuple[str, float, float, float, float, int]] = []
        self._id_map = {}  # Map global track ID to contiguous class label [0, N-1]
        self._parse_sequences()

    def _parse_sequences(self) -> None:
        """Parse ground truth annotations and build list of valid crop samples."""
        current_label = 0
        
        for seq in self.sequences:
            seq_dir = os.path.join(self.mot17_base_dir, seq)
            if not os.path.exists(seq_dir):
                # Try alternate matching folder
                matched = [d for d in os.listdir(self.mot17_base_dir) if seq.split("-")[0] in d and seq.split("-")[1] in d]
                if matched:
                    seq_dir = os.path.join(self.mot17_base_dir, matched[0])
                else:
                    continue

            gt_file = os.path.join(seq_dir, "gt", "gt.txt")
            img_dir = os.path.join(seq_dir, "img1")

            if not os.path.exists(gt_file) or not os.path.exists(img_dir):
                continue

            with open(gt_file, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) < 8:
                        continue

                    frame_idx = int(parts[0])
                    track_id = int(parts[1])
                    top = float(parts[2])
                    left = float(parts[3])
                    width = float(parts[4])
                    height = float(parts[5])
                    mark = int(parts[6])  # 1 = consider, 0 = ignore
                    class_id = int(parts[7])  # 1 = pedestrian
                    visibility = float(parts[8]) if len(parts) > 8 else 1.0

                    # Filter for valid pedestrian targets
                    if mark != 1 or class_id != 1 or visibility < self.min_visibility or height < self.min_height:
                        continue

                    img_path = os.path.join(img_dir, f"{frame_idx:06d}.jpg")
                    if not os.path.exists(img_path):
                        continue

                    # Create globally unique ID for this sequence track
                    global_id = f"{seq}_{track_id}"
                    if global_id not in self._id_map:
                        self._id_map[global_id] = current_label
                        current_label += 1

                    label = self._id_map[global_id]
                    self.samples.append((img_path, top, left, width, height, label))

        self.num_classes = current_label

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        img_path, top, left, width, height, label = self.samples[idx]

        img = cv2.imread(img_path)
        if img is None:
            # Fallback zero tensor if image unreadable
            return torch.zeros((3, self.crop_size[0], self.crop_size[1])), label

        h, w, _ = img.shape
        x1 = max(0, int(round(top)))
        y1 = max(0, int(round(left)))
        x2 = min(w, int(round(top + width)))
        y2 = min(h, int(round(left + height)))

        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            crop = cv2.resize(img, (self.crop_size[1], self.crop_size[0]))
        
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        tensor_crop = self.transform(crop_rgb)

        return tensor_crop, label
