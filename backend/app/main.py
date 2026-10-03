"""
FastAPI Main Application Entry Point.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.auth import router as auth_router
from backend.app.api.health import router as health_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.video import router as video_router
from backend.app.core.config import settings
from backend.app.db import database
from backend.app.db.database import Base
import backend.app.models  # Ensure models are imported for metadata registration

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        url_str = str(database.engine.url)
        if "postgresql" in url_str or "asyncpg" in url_str:
            logger.warning(
                f"[DB WARNING] Could not connect to PostgreSQL ({exc}). "
                "Falling back to local SQLite database (sqlite+aiosqlite:///./mot_db.db)..."
            )
            fallback_url = "sqlite+aiosqlite:///./mot_db.db"
            database.engine, database.AsyncSessionLocal = database.get_engine_and_sessionmaker(fallback_url)
            async with database.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise exc
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for video uploads & outputs
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(video_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": "Multi-Object Tracking System API",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
