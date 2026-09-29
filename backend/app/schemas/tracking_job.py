"""
Tracking Job Pydantic Schemas for Request & Response DTO Serialization.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class JobCreateRequest(BaseModel):
    video_id: str
    conf_threshold: float = 0.25
    max_cosine_distance: float = 0.20
    max_age: int = 30
    n_init: int = 1


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    user_id: str
    status: str
    progress: int
    config: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
