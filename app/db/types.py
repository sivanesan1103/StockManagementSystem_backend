"""Custom PostgreSQL type definitions and utilities."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import types
from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
    JSONB,
    DOUBLE_PRECISION,
)
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import SchemaType, TypeDecorator

# Re-export commonly used types for convenience
__all__ = [
    "UUID",
    "JSON",
    "DateTimeTZ",
    "Money",
]


# --- Custom Type Decorators ---

class UTCDateTime(TypeDecorator[datetime]):
    """
    DateTime that always stores and returns UTC.

    Uses TIMESTAMP WITH TIME ZONE on PostgreSQL.
    Automatically converts naive datetime to UTC on bind and
    ensures returned datetime is timezone-aware.
    """

    impl = types.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: Optional[datetime], dialect: Dialect
    ) -> Optional[datetime]:
        """Convert naive datetime to UTC before storing."""
        if value is None:
            return value
        if value.tzinfo is None:
            # Assume naive datetime is UTC
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(
        self, value: Optional[datetime], dialect: Dialect
    ) -> Optional[datetime]:
        """Ensure returned datetime is timezone-aware (should already be)."""
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class JSON(TypeDecorator[dict[str, Any]]):
    """
    JSON type that uses PostgreSQL's JSONB for better performance.

    Stores data as JSONB (binary JSON) for efficient querying.
    """

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        """Use JSONB on PostgreSQL, fall back to JSON on others."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        else:
            return dialect.type_descriptor(types.JSON)


class UUID(TypeDecorator):
    """
    UUID type that uses PostgreSQL's native UUID type.

    Stores UUIDs as native UUID type in PostgreSQL.
    By default, generates UUID4 if no value provided.
    """

    impl = PG_UUID(as_uuid=True)
    cache_ok = True

    def __init__(self, generate: bool = False, **kwargs: Any):
        """
        Initialize UUID type.

        Args:
            generate: If True, auto-generates UUID4 when None
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)
        self.generate = generate

    def process_bind_param(self, value: Optional[str], dialect: Dialect):
        """Generate UUID if needed and convert to proper format."""
        if value is None and self.generate:
            import uuid
            value = uuid.uuid4()
        return value


class Money(TypeDecorator[int]):
    """
    Money type stored as integer (smallest currency unit).

    Example: $10.99 stored as 1099 (cents)
    Provides automatic conversion between decimal and integer.
    """

    impl = types.BigInteger
    cache_ok = True

    def __init__(self, currency: str = "USD", **kwargs: Any):
        """
        Initialize Money type.

        Args:
            currency: Currency code (for documentation purposes)
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)
        self.currency = currency

    def process_bind_param(self, value: Optional[float], dialect: Dialect):
        """Convert decimal amount to integer cents."""
        if value is None:
            return None
        return int(value * 100)

    def process_result_value(self, value: Optional[int], dialect: Dialect):
        """Convert integer cents back to decimal amount."""
        if value is None:
            return None
        return value / 100.0


def register_custom_types() -> None:
    """
    Register custom types with SQLAlchemy/Alembic.

    This function can be called during application startup to ensure
    all custom types are properly registered with the dialect system.
    """
    # Simply importing this module registers the types via TypeDecorator
    pass
