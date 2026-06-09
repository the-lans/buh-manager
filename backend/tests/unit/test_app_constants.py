"""Unit tests for app_constants DB helpers."""

from decimal import Decimal
from uuid import uuid4

from sqlmodel import Session

from app.db.app_constants import (
    get_constant_decimal,
    get_constant_int,
    get_constant_value,
    upsert_constant,
)
from app.models.user import User


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
