from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current UTC time as naive datetime, compatible with SQLite storage."""
    return datetime.now(UTC).replace(tzinfo=None)
