"""
Video Repository Data Access Layer (Backend Persistence Tier).

Encapsulates direct SQLAlchemy ORM queries and database CRUD operations for Video entities.

Architectural Role:
- Executes async parameterized queries for creating video records and querying user video timelines.
- Leverages composite database index (`idx_videos_user_created`) for efficient sorting and filtering.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.video import Video


class VideoRepository:
    """
    Data access repository managing database operations for Video records.
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: Active request-scoped AsyncSession instance.
        """
        self.session = session

    async def get_by_id(self, video_id: str) -> Optional[Video]:
        """
        Query a Video record by primary key UUID.

        Args:
            video_id: Unique UUID string of target video asset.

        Returns:
            Video entity instance or None if not found.
        """
        return await self.session.get(Video, video_id)

    async def create(
        self,
        user_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        duration: Optional[float] = None,
        fps: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        frame_count: Optional[int] = None,
    ) -> Video:
        """
        Persist a new Video record into the database.

        Args:
            user_id: UUID of owning user.
            filename: Original uploaded filename.
            file_path: Absolute disk file path.
            file_size: Total file size in bytes.
            duration: Extracted duration in seconds.
            fps: Extracted frame rate.
            width: Frame width dimension in pixels.
            height: Frame height dimension in pixels.
            frame_count: Total frame count.

        Returns:
            Newly created and refreshed Video ORM instance.
        """
        video = Video(
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            frame_count=frame_count,
        )
        self.session.add(video)
        await self.session.commit()
        await self.session.refresh(video)
        return video

    async def list_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Video]:
        """
        Fetch a paginated list of Video records owned by a specific user ordered by creation date.

        Args:
            user_id: UUID of target user.
            limit: Maximum number of records to return.
            offset: Pagination offset count.

        Returns:
            List of Video entity instances matching query criteria.
        """
        stmt = (
            select(Video)
            .where(Video.user_id == user_id)
            .order_by(Video.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
