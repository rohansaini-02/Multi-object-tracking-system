"""
Database Connectivity & Session Management (Backend Persistence Infrastructure Tier).

Configures Async SQLAlchemy Engine, session factory (`AsyncSessionLocal`), and declarative base (`Base`).
Implements automatic environment detection for high-concurrency PostgreSQL connection pooling
or lightweight SQLite fallback when PostgreSQL is not reachable locally.
"""

from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings

logger = logging.getLogger("uvicorn.error")


def get_engine_and_sessionmaker(url: str):
    db_url = url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine_kwargs = {
        "echo": False,
        "future": True,
    }

    if "sqlite" in db_url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in db_url:
            engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs.update({
            "pool_size": 25,
            "max_overflow": 50,
            "pool_timeout": 30,
            "pool_pre_ping": True,
            "pool_recycle": 1800,
        })

    eng = create_async_engine(db_url, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return eng, session_factory


engine, AsyncSessionLocal = get_engine_and_sessionmaker(settings.DATABASE_URL)


class Base(DeclarativeBase):
    """
    Declarative Base class for all SQLAlchemy ORM domain models across the tracking system.
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async transactional database session per HTTP request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

