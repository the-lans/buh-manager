from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.config import settings


def utcnow() -> datetime:
    """Current UTC time as naive datetime, compatible with SQLite storage."""
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_to_utc(dt: datetime) -> datetime:
    """Normalize any datetime to naive UTC for storage.

    Tz-aware input  → convert to UTC, strip tzinfo.
    Naive input     → assume app_timezone (Europe/Moscow), then convert to UTC.

    Russian fiscal/banking data typically arrives as Moscow wall-clock time
    without an explicit offset, so naive strings are treated as Moscow time.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt.replace(tzinfo=ZoneInfo(settings.app_timezone)).astimezone(UTC).replace(tzinfo=None)


def utc_to_app_timezone(dt: datetime) -> datetime:
    """Interpret stored naive UTC datetime in app timezone."""
    return dt.replace(tzinfo=UTC).astimezone(ZoneInfo(settings.app_timezone))
