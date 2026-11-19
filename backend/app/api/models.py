"""
API Router for Model Weights & Re-ID Fine-Tuning Management.
"""

import asyncio
from datetime import datetime
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.api.auth import get_current_user
from backend.app.models.user import User

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/models", tags=["Models & Training"])

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
WEIGHTS_DIR = os.path.join(REPO_ROOT, "weights")
MOT17_DIR = os.path.join(REPO_ROOT, "data", "mot17")

# Global in-memory training execution state
_TRAINING_STATE: Dict[str, Any] = {
    "is_training": False,
    "status": "IDLE",  # IDLE, RUNNING, COMPLETED, FAILED
    "current_epoch": 0,
    "total_epochs": 0,
    "current_loss": None,
    "current_accuracy": None,
    "history": [],
    "started_at": None,
    "elapsed_seconds": 0,
    "output_weights": "weights/reid_fine_tuned.pth",
    "error": None,
    "logs": [],
}
_TRAINING_LOCK = threading.Lock()


class TrainReidRequest(BaseModel):
    epochs: int = Field(default=5, ge=1, le=50)
    batch_size: int = Field(default=32, ge=8, le=128)
    lr: float = Field(default=0.001, gt=0, le=0.1)


class WeightOption(BaseModel):
    id: str
    name: str
    filename: str
    path: str
    size_mb: Optional[float] = None
    modified_at: Optional[str] = None
    status: str  # READY, NOT_TRAINED
    description: str


def _get_available_weights() -> List[WeightOption]:
    """Scan the weights directory and build the catalog of selectable Re-ID weights."""
    catalog: List[WeightOption] = []

    # 1. Base appearance model (always available, uses torchvision ImageNet weights)
    catalog.append(
        WeightOption(
            id="base",
            name="Base ImageNet ResNet-18 (Default)",
            filename="Standard TorchVision ResNet18",
            path="base",
            size_mb=44.7,
            modified_at=None,
            status="READY",
            description="Default deep appearance extractor pretrained on ImageNet. Robust zero-shot representation.",
        )
    )

    # 2. Check for reid_fine_tuned.pth
    fine_tuned_path = os.path.join(WEIGHTS_DIR, "reid_fine_tuned.pth")
    if os.path.isfile(fine_tuned_path):
        stat = os.stat(fine_tuned_path)
        catalog.append(
            WeightOption(
                id="fine_tuned",
                name="Fine-Tuned MOT17 Re-ID",
                filename="reid_fine_tuned.pth",
                path="weights/reid_fine_tuned.pth",
                size_mb=round(stat.st_size / (1024 * 1024), 2),
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                status="READY",
                description="Custom appearance embedding model fine-tuned on MOT17 pedestrian crops for higher ID consistency.",
            )
        )
    else:
        catalog.append(
            WeightOption(
                id="fine_tuned",
                name="Fine-Tuned MOT17 Re-ID",
                filename="reid_fine_tuned.pth",
                path="weights/reid_fine_tuned.pth",
                size_mb=None,
                modified_at=None,
                status="NOT_TRAINED",
                description="Fine-tuned appearance weights. Trigger training below to generate this checkpoint.",
            )
        )

    # 3. Discover any additional custom .pth checkpoints in weights/
    if os.path.isdir(WEIGHTS_DIR):
        for fname in sorted(os.listdir(WEIGHTS_DIR)):
            if fname.endswith(".pth") and fname != "reid_fine_tuned.pth":
                fpath = os.path.join(WEIGHTS_DIR, fname)
                stat = os.stat(fpath)
                catalog.append(
                    WeightOption(
                        id=f"custom_{fname}",
                        name=f"Custom Checkpoint ({fname})",
                        filename=fname,
                        path=f"weights/{fname}",
                        size_mb=round(stat.st_size / (1024 * 1024), 2),
                        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        status="READY",
                        description="Custom PyTorch appearance weights checkpoint.",
                    )
                )

    return catalog


@router.get("/weights", response_model=List[WeightOption])
async def list_model_weights(
    current_user: User = Depends(get_current_user),
) -> List[WeightOption]:
    """Return all available Re-ID feature extractor weights."""
    return _get_available_weights()


@router.get("/train-reid/status")
async def get_training_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return the telemetry and progress status of the Re-ID fine-tuning job."""
    with _TRAINING_LOCK:
        state = dict(_TRAINING_STATE)
        if state["is_training"] and state["started_at"]:
            state["elapsed_seconds"] = round(time.time() - state["started_at"], 1)
        return state


def _run_training_worker(epochs: int, batch_size: int, lr: float):
    """Worker function executed in background thread."""
    global _TRAINING_STATE

    from ml.training.train_reid import train_reid_model

    output_path = os.path.join(WEIGHTS_DIR, "reid_fine_tuned.pth")

    def progress_callback(epoch: int, total: int, loss: float, acc: float):
        with _TRAINING_LOCK:
            _TRAINING_STATE["current_epoch"] = epoch
            _TRAINING_STATE["total_epochs"] = total
            _TRAINING_STATE["current_loss"] = round(loss, 4)
            _TRAINING_STATE["current_accuracy"] = round(acc, 2)
            _TRAINING_STATE["history"].append({
                "epoch": epoch,
                "loss": round(loss, 4),
                "accuracy": round(acc, 2),
                "timestamp": datetime.now().isoformat(),
            })
            _TRAINING_STATE["logs"].append(
                f"Epoch [{epoch}/{total}] - Loss: {loss:.4f} - Accuracy: {acc:.2f}%"
            )

    try:
        train_reid_model(
            mot17_dir=MOT17_DIR,
            output_weights_path=output_path,
            epochs=epochs,
            batch_size=batch_size,
            lr=lr,
            progress_callback=progress_callback,
        )

        with _TRAINING_LOCK:
            _TRAINING_STATE["is_training"] = False
            _TRAINING_STATE["status"] = "COMPLETED"
            _TRAINING_STATE["logs"].append("✓ Model training completed successfully and saved to weights/reid_fine_tuned.pth")

    except Exception as exc:
        logger.exception("[TRAINING ERROR] Re-ID fine-tuning failed: %s", exc)
        with _TRAINING_LOCK:
            _TRAINING_STATE["is_training"] = False
            _TRAINING_STATE["status"] = "FAILED"
            _TRAINING_STATE["error"] = str(exc)
            _TRAINING_STATE["logs"].append(f"❌ Training error: {str(exc)}")


@router.post("/train-reid", status_code=status.HTTP_202_ACCEPTED)
async def start_reid_training(
    req: TrainReidRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dispatch an asynchronous Re-ID appearance feature fine-tuning task."""
    global _TRAINING_STATE

    with _TRAINING_LOCK:
        if _TRAINING_STATE["is_training"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A training job is already in progress.",
            )

        # Reset state
        _TRAINING_STATE = {
            "is_training": True,
            "status": "RUNNING",
            "current_epoch": 0,
            "total_epochs": req.epochs,
            "current_loss": None,
            "current_accuracy": None,
            "history": [],
            "started_at": time.time(),
            "elapsed_seconds": 0,
            "output_weights": "weights/reid_fine_tuned.pth",
            "error": None,
            "logs": [f"🚀 Initiated Re-ID fine-tuning with {req.epochs} epochs, batch size {req.batch_size}, lr {req.lr}"],
        }

    # Start thread
    thread = threading.Thread(
        target=_run_training_worker,
        args=(req.epochs, req.batch_size, req.lr),
        daemon=True,
    )
    thread.start()

    return {"ok": True, "message": "Training job started.", "state": _TRAINING_STATE}

