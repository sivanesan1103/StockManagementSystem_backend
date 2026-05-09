"""Database models base class and custom type definitions."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    MetaData,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all database models with common fields."""

    metadata = metadata

    # Common audit fields - not required, but provided for convenience
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Optional UUID primary key - can be overridden in subclasses
    # from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    # id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())


def utc_now() -> datetime:
    """Return current UTC datetime with timezone."""
    return datetime.now(timezone.utc)
