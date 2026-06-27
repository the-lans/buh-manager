"""Unit tests for dt utility — normalize_to_utc.

DB stores naive UTC datetimes.  normalize_to_utc guarantees that:
  • Naive inputs  → assumed Europe/Moscow (UTC+3) → subtract 3h → naive UTC
  • Aware inputs  → convert to UTC → strip tzinfo → naive UTC
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.utils.dt import normalize_to_utc, utcnow

MOSCOW = ZoneInfo("Europe/Moscow")  # UTC+3, no DST since 2014
YEKATERINBURG = ZoneInfo("Asia/Yekaterinburg")  # UTC+5
NEW_YORK = ZoneInfo("America/New_York")  # UTC-4 (summer)


# ── Naive inputs (assumed Moscow) ─────────────────────────────────────────────

@pytest.mark.parametrize("naive_input,expected_utc", [
    # Moscow midnight crosses the calendar day boundary
    (datetime(2026, 6, 1, 0, 0, 0),           datetime(2026, 5, 31, 21, 0, 0)),
    # Moscow 3 am = UTC midnight (same calendar day)
    (datetime(2026, 6, 1, 3, 0, 0),            datetime(2026, 6, 1, 0, 0, 0)),
    # Last second of Moscow-June (23:59:59 MSK = 20:59:59 UTC)
    (datetime(2026, 6, 30, 23, 59, 59),        datetime(2026, 6, 30, 20, 59, 59)),
    # Year boundary: Moscow midnight Jan 1 → Dec 31 21:00 UTC
    (datetime(2026, 1, 1, 0, 0, 0),            datetime(2025, 12, 31, 21, 0, 0)),
    # Last second of Moscow year (Dec 31 23:59:59 MSK = Dec 31 20:59:59 UTC)
    (datetime(2026, 12, 31, 23, 59, 59),       datetime(2026, 12, 31, 20, 59, 59)),
    # Midday — no boundary crossing
    (datetime(2026, 6, 15, 12, 0, 0),          datetime(2026, 6, 15, 9, 0, 0)),
    # Moscow 00:30 — still crosses to previous UTC day
    (datetime(2026, 3, 1, 0, 30, 0),           datetime(2026, 2, 28, 21, 30, 0)),
])
def test_normalize_naive_assumed_moscow(naive_input: datetime, expected_utc: datetime) -> None:
    """Naive datetime assumed to be Moscow wall-clock; result must be naive UTC."""
    result = normalize_to_utc(naive_input)
    assert result == expected_utc, f"{naive_input} MSK → expected {expected_utc} UTC, got {result}"
    assert result.tzinfo is None


# ── UTC-aware inputs ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("aware_input,expected_utc", [
    # UTC-aware — value unchanged, tzinfo stripped
    (datetime(2026, 5, 31, 21, 0, 0, tzinfo=UTC), datetime(2026, 5, 31, 21, 0, 0)),
    (datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),   datetime(2026, 6, 1, 0, 0, 0)),
    # UTC midnight year-start
    (datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),   datetime(2026, 1, 1, 0, 0, 0)),
])
def test_normalize_utc_aware_strips_tzinfo(aware_input: datetime, expected_utc: datetime) -> None:
    """UTC-aware datetime: value is unchanged, tzinfo stripped."""
    result = normalize_to_utc(aware_input)
    assert result == expected_utc
    assert result.tzinfo is None


# ── Non-UTC aware inputs ───────────────────────────────────────────────────────

@pytest.mark.parametrize("aware_input,expected_utc", [
    # Moscow-aware midnight June 1 → UTC 21:00 May 31 (same as naive Moscow case)
    (datetime(2026, 6, 1, 0, 0, 0, tzinfo=MOSCOW),   datetime(2026, 5, 31, 21, 0, 0)),
    # Moscow-aware 3am June 1 → UTC midnight June 1
    (datetime(2026, 6, 1, 3, 0, 0, tzinfo=MOSCOW),   datetime(2026, 6, 1, 0, 0, 0)),
    # Yekaterinburg (UTC+5) midnight → subtract 5h
    (datetime(2026, 6, 1, 0, 0, 0, tzinfo=YEKATERINBURG), datetime(2026, 5, 31, 19, 0, 0)),
    # New York (UTC-4 summer) midnight → add 4h
    (datetime(2026, 6, 1, 0, 0, 0, tzinfo=NEW_YORK), datetime(2026, 6, 1, 4, 0, 0)),
])
def test_normalize_non_utc_aware_converts_to_utc(aware_input: datetime, expected_utc: datetime) -> None:
    """Non-UTC aware datetimes are converted to UTC and tzinfo stripped."""
    result = normalize_to_utc(aware_input)
    assert result == expected_utc
    assert result.tzinfo is None


# ── Equivalence: naive Moscow == Moscow-aware == corresponding UTC-aware ───────

@pytest.mark.parametrize("naive_moscow,moscow_aware,utc_aware", [
    (
        datetime(2026, 6, 1, 0, 0, 0),
        datetime(2026, 6, 1, 0, 0, 0, tzinfo=MOSCOW),
        datetime(2026, 5, 31, 21, 0, 0, tzinfo=UTC),
    ),
    (
        datetime(2026, 6, 30, 23, 59, 59),
        datetime(2026, 6, 30, 23, 59, 59, tzinfo=MOSCOW),
        datetime(2026, 6, 30, 20, 59, 59, tzinfo=UTC),
    ),
    (
        datetime(2026, 1, 1, 0, 0, 0),
        datetime(2026, 1, 1, 0, 0, 0, tzinfo=MOSCOW),
        datetime(2025, 12, 31, 21, 0, 0, tzinfo=UTC),
    ),
])
def test_three_representations_of_same_instant_normalize_identically(
    naive_moscow: datetime,
    moscow_aware: datetime,
    utc_aware: datetime,
) -> None:
    """All three representations of the same instant must normalize to the same naive UTC value."""
    result_naive = normalize_to_utc(naive_moscow)
    result_moscow = normalize_to_utc(moscow_aware)
    result_utc = normalize_to_utc(utc_aware)
    assert result_naive == result_moscow == result_utc
    assert result_naive.tzinfo is None


# ── utcnow ────────────────────────────────────────────────────────────────────

def test_utcnow_is_naive() -> None:
    now = utcnow()
    assert now.tzinfo is None


def test_utcnow_is_close_to_real_utc() -> None:
    now = utcnow()
    real_utc = datetime.now(UTC).replace(tzinfo=None)
    diff = abs((real_utc - now).total_seconds())
    assert diff < 5
