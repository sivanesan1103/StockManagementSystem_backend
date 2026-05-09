"""FastAPI integration for automatic database migrations on startup."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from .session import close_db, get_engine, init_engine
from .types import register_custom_types

logger = logging.getLogger(__name__)

# Flag to track if migrations have been run
_migrations_run: bool = False


def should_run_migrations() -> bool:
    """
    Check if automatic migrations should be run on startup.

    Returns:
        True if AUTO_RUN_MIGRATIONS env var is set to "true" (case-insensitive)
    """
    return os.getenv("AUTO_RUN_MIGRATIONS", "false").lower() == "true"


def run_migrations_sync(database_url: Optional[str] = None) -> None:
    """
    Run database migrations synchronously.

    This function is intended to be called during application startup.
    It runs Alembic migrations to bring the database up to date.

    Args:
        database_url: Optional database URL. If not provided, uses settings.

    Raises:
        RuntimeError: If migrations fail to run
    """
    global _migrations_run

    if _migrations_run:
        logger.debug("Migrations already run, skipping")
        return

    try:
        # Import here to avoid circular imports
        from alembic import command
        from alembic.config import Config

        # Register custom types before running migrations
        register_custom_types()

        # Get project root
        current_file = __file__
        current_dir = os.path.dirname(os.path.abspath(current_file))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        alembic_ini = os.path.join(project_root, "alembic.ini")

        if not os.path.exists(alembic_ini):
            logger.warning(
                f"alembic.ini not found at {alembic_ini}, skipping migrations"
            )
            return

        config = Config(alembic_ini)

        # Override database URL if provided
        if database_url:
            config.set_main_option("sqlalchemy.url", database_url)

        # Run upgrade to head
        logger.info("Running database migrations...")
        command.upgrade(config, "head")
        logger.info("Database migrations completed successfully")

        _migrations_run = True

    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


async def run_migrations_async(database_url: Optional[str] = None) -> None:
    """
    Run database migrations asynchronously.

    Args:
        database_url: Optional database URL
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: run_migrations_sync(database_url=database_url)
    )


def setup_migration_events(app: FastAPI, database_url: Optional[str] = None) -> None:
    """
    Configure FastAPI startup/shutdown events for migrations.

    Adds event handlers to the FastAPI app that:
    - Initialize database engine on startup
    - Optionally run migrations on startup
    - Close database connections on shutdown

    Args:
        app: FastAPI application instance
        database_url: Optional database URL to use
    """

    @app.on_event("startup")
    async def startup_db() -> None:
        """Initialize database and optionally run migrations."""
        # Import settings (avoid circular imports)
        try:
            from app.core.config import settings

            db_url = database_url or str(settings.database_url)
        except ImportError:
            # Fallback to environment variable
            db_url = database_url or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

        if not db_url:
            logger.warning("No database URL configured, skipping database initialization")
            return

        # Initialize engine
        init_engine(db_url)
        logger.info("Database engine initialized")

        # Check connection health
        from .session import check_db_connection

        if not await check_db_connection():
            logger.error("Database connection check failed")
            raise RuntimeError("Could not connect to database")

        logger.info("Database connection established")

        # Optionally run migrations
        if should_run_migrations():
            try:
                await run_migrations_async(db_url)
            except Exception as e:
                logger.error(f"Migration failed: {e}")
                # In development, you might want to fail fast
                # In production, you might want to continue or raise
                if os.getenv("ENVIRONMENT", "development") == "production":
                    raise
        else:
            logger.info("Auto-migrations disabled (AUTO_RUN_MIGRATIONS=false)")

    @app.on_event("shutdown")
    async def shutdown_db() -> None:
        """Close database connections."""
        await close_db()
        logger.info("Database connections closed")


def get_migration_status() -> dict[str, Optional[str]]:
    """
    Get current migration status.

    Returns:
        Dictionary with 'current_revision' and 'latest_revision'
    """
    try:
        from alembic.command import current
        from alembic.config import Config

        import io
        from contextlib import redirect_stdout

        config = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))

        # Capture current revision output
        f = io.StringIO()
        with redirect_stdout(f):
            current(config)
        output = f.getvalue().strip()

        # Parse output (format: "Current revision(s): <rev>")
        current_rev = None
        if output:
            parts = output.split()
            if len(parts) >= 3:
                current_rev = parts[2]

        return {
            "current_revision": current_rev,
            "latest_revision": None,  # Would need to parse history
        }
    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        return {"current_revision": None, "latest_revision": None}
