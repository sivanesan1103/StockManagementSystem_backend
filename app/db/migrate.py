"""Database migration utilities and CLI."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
from alembic import command
from alembic.config import Config


def get_alembic_config(database_url: Optional[str] = None) -> Config:
    """
    Get Alembic configuration object.

    Args:
        database_url: Optional database URL to override settings

    Returns:
        Configured Alembic Config object.
    """
    # Find the project root (assuming this file is in app/db/)
    current_file = Path(__file__).resolve()
    # Path: migrate.py -> db/ (parent) -> app/ (parent.parent) -> project_root/ (parent.parent.parent)
    project_root = current_file.parent.parent.parent
    alembic_ini = project_root / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {alembic_ini}. "
            "Make sure you're running from the project root."
        )

    config = Config(str(alembic_ini))

    # Override database URL if provided
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    else:
        # Try to get from environment
        db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        if db_url:
            config.set_main_option("sqlalchemy.url", db_url)

    return config


def upgrade(
    revision: str = "head",
    database_url: Optional[str] = None,
    sql: bool = False,
) -> None:
    """
    Upgrade database to a specific revision.

    Args:
        revision: Target revision (default: "head" for latest)
        database_url: Optional database URL
        sql: If True, generate SQL instead of executing
    """
    config = get_alembic_config(database_url)
    command.upgrade(config, revision, sql=sql)


def downgrade(
    revision: str = "-1",
    database_url: Optional[str] = None,
    sql: bool = False,
) -> None:
    """
    Downgrade database by one or to a specific revision.

    Args:
        revision: Target revision (default: "-1" for previous)
        database_url: Optional database URL
        sql: If True, generate SQL instead of executing
    """
    config = get_alembic_config(database_url)
    command.downgrade(config, revision, sql=sql)


def revision(
    message: str,
    autogenerate: bool = True,
    database_url: Optional[str] = None,
) -> None:
    """
    Create a new migration revision.

    Args:
        message: Migration message/description
        autogenerate: If True, auto-generate migration from model changes
        database_url: Optional database URL for autogenerate
    """
    config = get_alembic_config(database_url)
    command.revision(config, message=message, autogenerate=autogenerate)


def show_history(database_url: Optional[str] = None) -> None:
    """Show migration history."""
    config = get_alembic_config(database_url)
    command.history(config)


def current(database_url: Optional[str] = None) -> None:
    """Show current database revision."""
    config = get_alembic_config(database_url)
    command.current(config)


def stamp(
    revision: str = "head",
    database_url: Optional[str] = None,
    sql: bool = False,
) -> None:
    """
    Stamp database with a specific revision without running migrations.

    Useful for marking databases as up-to-date.

    Args:
        revision: Target revision
        database_url: Optional database URL
        sql: Generate SQL instead of executing
    """
    config = get_alembic_config(database_url)
    command.stamp(config, revision, sql=sql)


async def async_upgrade(
    revision: str = "head",
    database_url: Optional[str] = None,
) -> None:
    """
    Async wrapper for upgrade to use with asyncio.

    Args:
        revision: Target revision
        database_url: Optional database URL
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: upgrade(revision=revision, database_url=database_url)
    )


async def async_downgrade(
    revision: str = "-1",
    database_url: Optional[str] = None,
) -> None:
    """
    Async wrapper for downgrade.

    Args:
        revision: Target revision
        database_url: Optional database URL
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: downgrade(revision=revision, database_url=database_url)
    )


# --- CLI Interface ---

@click.group()
def cli() -> None:
    """Database migration management CLI."""
    pass


@cli.command()
@click.option("--revision", default="head", help="Target revision")
@click.option("--database-url", help="Database URL")
@click.option("--sql", is_flag=True, help="Generate SQL instead of executing")
def up(revision: str, database_url: Optional[str], sql: bool) -> None:
    """Upgrade database to latest or specified revision."""
    upgrade(revision=revision, database_url=database_url, sql=sql)


@cli.command()
@click.option("--revision", default="-1", help="Target revision")
@click.option("--database-url", help="Database URL")
@click.option("--sql", is_flag=True, help="Generate SQL instead of executing")
def down(revision: str, database_url: Optional[str], sql: bool) -> None:
    """Downgrade database by one or to specified revision."""
    downgrade(revision=revision, database_url=database_url, sql=sql)


@cli.command()
@click.argument("message")
@click.option("--no-autogenerate", is_flag=True, help="Create empty migration")
def new(message: str, no_autogenerate: bool) -> None:
    """Create a new migration revision."""
    revision(message=message, autogenerate=not no_autogenerate)


@cli.command()
def hist() -> None:
    """Show migration history."""
    show_history()


@cli.command()
def cur() -> None:
    """Show current revision."""
    current()


if __name__ == "__main__":
    cli()
