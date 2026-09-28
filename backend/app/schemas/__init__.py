"""
Schemas Package Init
"""

from backend.app.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from backend.app.schemas.video import VideoResponse

__all__ = ["UserCreate", "UserLogin", "Token", "UserResponse", "VideoResponse"]
