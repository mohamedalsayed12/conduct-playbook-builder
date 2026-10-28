"""Injectable timezone-aware UTC clock."""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Return the current time as timezone-aware UTC."""
    return datetime.now(UTC)
