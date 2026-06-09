"""Unit tests for app_constants DB helpers."""

from decimal import Decimal

import pytest
from sqlmodel import Session

import app.utils.ttl_cache as _ttl_mod
from app.db.app_constants import (
    CONSTANTS_CACHE_TTL,
    _cache,
    get_constant_decimal,
    get_constant_int,
    get_constant_value,
    upsert_constant,
)
from app.models.user import User


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Isolate TTL cache between tests."""
    _cache.clear()
    yield
    _cache.clear()


def test_get_constant_returns_none_when_not_in_db(session: Session, test_user: User) -> None:
    assert get_constant_value(session=session, user_id=test_user.id, key="MISSING") is None


def test_get_constant_uses_default_decimal_when_not_in_db(session: Session, test_user: User) -> None:
    default = Decimal("5.0")
    result = get_constant_decimal(session=session, user_id=test_user.id, key="MISSING", default=default)
    assert result == default


def test_get_constant_uses_default_int_when_not_in_db(session: Session, test_user: User) -> None:
    result = get_constant_int(session=session, user_id=test_user.id, key="MISSING", default=42)
    assert result == 42


def test_upsert_creates_constant(session: Session, test_user: User) -> None:
    row = upsert_constant(session=session, user_id=test_user.id, key="MY_KEY", value="99")
    assert row.key == "MY_KEY"
    assert row.value == "99"
    assert get_constant_value(session=session, user_id=test_user.id, key="MY_KEY") == "99"


def test_upsert_updates_existing_constant(session: Session, test_user: User) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="MY_KEY", value="1")
    upsert_constant(session=session, user_id=test_user.id, key="MY_KEY", value="2")
    assert get_constant_value(session=session, user_id=test_user.id, key="MY_KEY") == "2"


def test_get_constant_decimal_parses_string(session: Session, test_user: User) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="TOL", value="1.5")
    result = get_constant_decimal(session=session, user_id=test_user.id, key="TOL", default=Decimal("0"))
    assert result == Decimal("1.5")


def test_get_constant_int_parses_string(session: Session, test_user: User) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="HOURS", value="24")
    result = get_constant_int(session=session, user_id=test_user.id, key="HOURS", default=12)
    assert result == 24


def test_get_constant_decimal_falls_back_on_invalid(session: Session, test_user: User) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="BAD", value="not-a-number")
    result = get_constant_decimal(session=session, user_id=test_user.id, key="BAD", default=Decimal("7"))
    assert result == Decimal("7")


def test_get_constant_int_falls_back_on_invalid(session: Session, test_user: User) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="BAD", value="not-a-number")
    result = get_constant_int(session=session, user_id=test_user.id, key="BAD", default=10)
    assert result == 10


def test_constants_are_scoped_per_user(session: Session, test_user: User, second_test_user: User) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="K", value="user1_val")
    upsert_constant(session=session, user_id=second_test_user.id, key="K", value="user2_val")
    assert get_constant_value(session=session, user_id=test_user.id, key="K") == "user1_val"
    assert get_constant_value(session=session, user_id=second_test_user.id, key="K") == "user2_val"


# ── TTL cache behaviour ───────────────────────────────────────────────────────


def test_cache_hit_avoids_second_db_query(
    session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="C", value="42")
    # First call populates cache
    get_constant_value(session=session, user_id=test_user.id, key="C")
    # Poison the DB row so a cache miss would return different data
    monkeypatch.setattr(session.__class__, "exec", lambda *_, **__: (_ for _ in ()).throw(RuntimeError("unexpected DB call")))
    # Second call must hit cache and not touch the DB
    result = get_constant_value(session=session, user_id=test_user.id, key="C")
    assert result == "42"


def test_cache_expires_after_ttl(
    session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="C", value="old")
    get_constant_value(session=session, user_id=test_user.id, key="C")
    # Simulate TTL expiry: advance monotonic past the expiry point
    real_monotonic = _ttl_mod.time.monotonic
    monkeypatch.setattr(_ttl_mod.time, "monotonic", lambda: real_monotonic() + CONSTANTS_CACHE_TTL + 1)
    result = get_constant_value(session=session, user_id=test_user.id, key="C")
    assert result == "old"  # value from DB is the same; confirms DB was re-queried (no error)


def test_upsert_invalidates_cache(session: Session, test_user: User) -> None:
    upsert_constant(session=session, user_id=test_user.id, key="C", value="1")
    # Warm the cache
    get_constant_value(session=session, user_id=test_user.id, key="C")
    cache_key = (str(test_user.id), "C")
    assert _cache.get(cache_key)[0] is True  # cache hit
    # Update — must evict cache
    upsert_constant(session=session, user_id=test_user.id, key="C", value="2")
    assert _cache.get(cache_key)[0] is False  # cache miss after invalidation
    assert get_constant_value(session=session, user_id=test_user.id, key="C") == "2"


def test_cache_stores_none_for_missing_key(session: Session, test_user: User) -> None:
    get_constant_value(session=session, user_id=test_user.id, key="NO")
    cache_key = (str(test_user.id), "NO")
    hit, value = _cache.get(cache_key)
    assert hit is True
    assert value is None
