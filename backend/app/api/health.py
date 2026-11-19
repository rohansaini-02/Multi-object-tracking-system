"""
Healthcheck endpoint router.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
import torch

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str
    version: str
    device: Optional[str] = None
    cuda_available: Optional[bool] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify backend operational state and compute hardware."""
    cuda_avail = torch.cuda.is_available()
    device_name = f"CUDA ({torch.cuda.get_device_name(0)})" if cuda_avail else f"CPU (PyTorch {torch.__version__})"
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        service="Multi-Object Tracking Backend",
        version="0.1.0",
        device=device_name,
        cuda_available=cuda_avail,
    )

