"""Alembic environment configuration for async SQLAlchemy."""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Any, Optional

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

# Add the project root directory to the Python path
# This allows imports from the app package.
# Project root is 3 levels up from here: migrations/ -> db/ -> app/ -> project_root/
current_file = Path(__file__).resolve()
project_root = current_file.parents[3]  # Go up 3: migrations->db->app->project_root
sys.path.insert(0, str(project_root))

# Import your application's database configuration
# This will be available after creating the core config module
try:
    from app.core.config import settings
    from app.db.base import Base, metadata
    from app.db.session import init_engine
except ImportError:
    # Fallback for when config is not yet available
    settings = None
    Base = None
    metadata = None

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)


def get_database_url() -> str:
    """
    Get database URL from settings or environment.

    Returns:
        Database connection URL.
    """
    if settings and hasattr(settings, 'DATABASE_URL'):
        return str(settings.DATABASE_URL)

    # Fallback to environment variable
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL or POSTGRES_URL environment variable must be set"
        )
    return database_url


def get_sync_database_url(url: str) -> str:
    """
    Convert async PostgreSQL URL to sync version for Alembic.

    Alembic doesn't fully support async engines, so we use a sync driver
    for migrations while the application uses asyncpg.

    Args:
        url: Async database URL (postgresql+asyncpg://)

    Returns:
        Sync database URL (postgresql:// or postgresql+psycopg://)
    """
    # Replace asyncpg driver with psycopg for migrations
    sync_url = url.replace("postgresql+asyncpg://", "postgresql://")
    sync_url = sync_url.replace("postgresql+psycopg://", "postgresql://")
    return sync_url


def include_object(
    object: Any,
    name: str,
    type_: str,
    reflected: bool,
    compare_to: Any,
) -> bool:
    """
    Filter function to control which objects are included in migrations.

    Args:
        object: The database object
        name: Object name
        type_: Object type (table, column, index, etc.)
        reflected: Whether object was reflected from database
        compare_to: Object being compared

    Returns:
        True to include the object, False to exclude
    """
    # Exclude alembic_version table from automatic generation
    if type_ == "table" and name == "alembic_version":
        return False
    return True


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    sync_url = get_sync_database_url(url)

    context.configure(
        url=sync_url,
        target_metadata=metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations with the given connection.

    Args:
        connection: SQLAlchemy Connection object.
    """
    context.configure(
        connection=connection,
        target_metadata=metadata,
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Get sync URL for Alembic (it doesn't support asyncpg yet)
    async_url = get_database_url()
    sync_url = get_sync_database_url(async_url)

    # Create sync engine for migrations
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        # Import psycopg driver for sync connections
        from sqlalchemy import create_engine

        connectable = create_engine(
            sync_url,
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        do_run_migrations(connection)


def run_async_migrations() -> None:
    """
    Entry point for async migration execution.
    This wraps the sync migration logic in an async context.
    """
    asyncio.run(run_migrations_online())


# Determine the migration mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_async_migrations()
