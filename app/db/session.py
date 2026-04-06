from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.db.base import Base


def create_db_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.db_url,
        echo=settings.db_echo,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    from app.db.models import (  # noqa: F401
        AttendanceRecord,
        AttendanceSession,
        AuditLog,
        Branch,
        Company,
        CompanyAdminInvite,
        Department,
        Employee,
        LeaveRequest,
        Shift,
        User,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if connection.dialect.name == "postgresql":
            await connection.execute(
                text(
                    """
                    ALTER TABLE attendance_sessions
                    ALTER COLUMN video_note_file_id TYPE TEXT
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    ALTER TABLE attendance_sessions
                    ALTER COLUMN video_note_file_unique_id TYPE TEXT
                    """
                )
            )
