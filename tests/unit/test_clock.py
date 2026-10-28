"""Unit tests for the injectable UTC clock."""

from datetime import UTC

from app.clock import utc_now


def test_utc_now_is_timezone_aware_utc() -> None:
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(None)
