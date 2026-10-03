"""
Healthcheck endpoint router.
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify backend operational state."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        service="Multi-Object Tracking Backend",
        version="0.1.0",
    )
