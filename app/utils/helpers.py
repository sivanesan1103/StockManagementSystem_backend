"""Common helper functions for the application.

This module provides reusable utility functions for common operations
such as date/time formatting, ID generation, and string manipulation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional


def generate_uuid() -> str:
    """Generate a unique identifier using UUID4.

    Returns:
        str: A randomly generated UUID4 as a string.

    Example:
        >>> uid = generate_uuid()
        >>> print(uid)
        '550e8400-e29b-41d4-a716-446655440000'
    """
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get the current UTC datetime with timezone info.

    Returns:
        datetime: Current datetime in UTC timezone.

    Example:
        >>> now = utc_now()
        >>> print(now)
        '2024-01-15 10:30:00+00:00'
    """
    return datetime.now(timezone.utc)


def format_datetime(
    dt: datetime,
    fmt: str = "%Y-%m-%d %H:%M:%S",
    timezone: Optional[timezone] = None,
) -> str:
    """Format a datetime object to a string.

    Args:
        dt: The datetime object to format.
        fmt: The format string (default: "%Y-%m-%d %H:%M:%S").
        timezone: Optional timezone to convert to before formatting.

    Returns:
        str: Formatted datetime string.

    Example:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> format_datetime(dt, "%Y/%m/%d")
        '2024/01/15'
    """
    if timezone is not None:
        dt = dt.astimezone(timezone)
    return dt.strftime(fmt)


def iso_format(dt: datetime) -> str:
    """Format a datetime as ISO 8601 string.

    Args:
        dt: The datetime object to format.

    Returns:
        str: ISO 8601 formatted datetime string.

    Example:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> iso_format(dt)
        '2024-01-15T10:30:00+00:00'
    """
    return dt.isoformat()


def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse an ISO 8601 formatted datetime string.

    Args:
        iso_string: ISO 8601 formatted datetime string.

    Returns:
        datetime: Parsed datetime object with timezone.

    Raises:
        ValueError: If the string cannot be parsed.

    Example:
        >>> dt = parse_iso_datetime("2024-01-15T10:30:00+00:00")
        >>> print(dt)
        '2024-01-15 10:30:00+00:00'
    """
    try:
        return datetime.fromisoformat(iso_string)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid ISO datetime format: {iso_string}") from e


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a maximum length with an optional suffix.

    Args:
        text: The string to truncate.
        max_length: Maximum length including suffix (default: 100).
        suffix: Suffix to append when truncated (default: "...").

    Returns:
        str: Truncated string with suffix if needed.

    Example:
        >>> truncate_string("This is a very long text", 15)
        'This is a very ...'
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def camel_to_snake(name: str) -> str:
    """Convert a CamelCase string to snake_case.

    Args:
        name: The CamelCase string to convert.

    Returns:
        str: The converted snake_case string.

    Example:
        >>> camel_to_snake("CamelCaseName")
        'camel_case_name'
    """
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(name: str) -> str:
    """Convert a snake_case string to CamelCase.

    Args:
        name: The snake_case string to convert.

    Returns:
        str: The converted CamelCase string.

    Example:
        >>> snake_to_camel("snake_case_name")
        'SnakeCaseName'
    """
    components = name.split("_")
    return "".join(x.capitalize() for x in components)


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID.

    Args:
        value: The string to validate.

    Returns:
        bool: True if valid UUID, False otherwise.

    Example:
        >>> is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False
