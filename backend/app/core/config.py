"""
Application configuration management using Pydantic Settings.
Reads environment variables from root or backend .env file.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Object Tracking System API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-change-in-production-123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database & Redis settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mot_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    # Paths
    UPLOAD_DIR: str = "data/uploads"
    OUTPUT_DIR: str = "data/outputs"
    RESULTS_DIR: str = "data/results"
    MOT17_DIR: str = "data/mot17"
    WEIGHTS_DIR: str = "weights"

    # ML Config
    YOLO_MODEL_PATH: str = "weights/yolov8m.pt"
    REID_BASE_WEIGHTS_PATH: str = "weights/reid_base.pth"
    REID_FINETUNED_WEIGHTS_PATH: str = "weights/reid_fine_tuned.pth"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
