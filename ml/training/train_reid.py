"""
PyTorch Fine-Tuning Script for Re-ID Appearance Feature Embedding Model.
"""

from typing import List, Optional
import logging
import os
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.tracker.reid_feature_extractor import Net
from ml.training.dataset import MOT17CropDataset

logger = logging.getLogger(__name__)


class ReidClassifier(nn.Module):
    """Combines Re-ID feature extractor backbone with a classification head for training."""

    def __init__(self, num_classes: int, reid_dim: int = 128, pretrained: bool = True):
        super(ReidClassifier, self).__init__()
        self.net = Net(reid_dim=reid_dim, pretrained=pretrained)
        self.classifier = nn.Linear(reid_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.net(x)
        logits = self.classifier(features)
        return logits


def train_reid_model(
    mot17_dir: str = "data/mot17",
    output_weights_path: str = "weights/reid_fine_tuned.pth",
    epochs: int = 10,
    batch_size: int = 32,
    lr: float = 1e-3,
    feature_dim: int = 128,
    train_sequences: Optional[List[str]] = None,
    device: Optional[str] = None,
) -> str:
    """Train/Fine-tune Re-ID feature embedding model on MOT17 cropped dataset.

    Args:
        mot17_dir: Root MOT17 dataset directory.
        output_weights_path: Output file path for trained PyTorch weights (.pth).
        epochs: Number of training epochs.
        batch_size: DataLoader batch size.
        lr: Learning rate.
        feature_dim: Dimension of output embedding vector (e.g. 128).
        train_sequences: Sequences to use for training split.
        device: 'cuda', 'cpu', or auto.

    Returns:
        Path to saved fine-tuned weight file.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    dev = torch.device(device)
    logger.info("Using device: %s", dev)

    # 1. Initialize dataset and dataloader
    dataset = MOT17CropDataset(
        mot17_base_dir=mot17_dir,
        sequences=train_sequences,
    )
    if len(dataset) == 0:
        raise ValueError(
            f"No valid training crop samples found in '{mot17_dir}'. Please ensure MOT17 dataset is placed there."
        )

    logger.info("Dataset loaded: %d crops across %d identities.", len(dataset), dataset.num_classes)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

    # 2. Build model, optimizer, loss
    model = ReidClassifier(num_classes=dataset.num_classes, reid_dim=feature_dim, pretrained=True)
    model.to(dev)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    # 3. Training Loop
    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs, targets = inputs.to(dev), targets.to(dev)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

        scheduler.step()
        epoch_loss = running_loss / total
        epoch_acc = 100.0 * correct / total
        logger.info("Epoch [%d/%d] - Loss: %.4f - Accuracy: %.2f%%", epoch, epochs, epoch_loss, epoch_acc)

    # 4. Save fine-tuned backbone weights (extracting .net state dict)
    os.makedirs(os.path.dirname(os.path.abspath(output_weights_path)), exist_ok=True)
    torch.save(model.net.state_dict(), output_weights_path)
    elapsed = time.time() - start_time
    logger.info("Training completed in %.1fs. Saved weights to %s", elapsed, output_weights_path)

    return output_weights_path
