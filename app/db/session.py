"""Database session management for async SQLAlchemy."""

from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .base import Base

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine(database_url: str) -> AsyncEngine:
    """
    Initialize the async database engine.

    Args:
        database_url: Async PostgreSQL URL (postgresql+asyncpg://)

    Returns:
        The created AsyncEngine instance.
    """
    global _engine, _session_factory

    _engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    return _engine


def get_engine() -> AsyncEngine:
    """Get the current async engine instance."""
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. Call init_engine() first."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the current session factory."""
    if _session_factory is None:
        raise RuntimeError(
            "Session factory not initialized. Call init_engine() first."
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get a database session.

    Yields:
        An async database session that will be automatically closed.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_db() -> None:
    """Close database connections - call on application shutdown."""
    if _engine is not None:
        await _engine.dispose()
