import time
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlmodel import Session, select

from app.models.app_constant import AppConstant

CONSTANTS_CACHE_TTL: float = 10.0

# (str(user_id), key) -> (value_or_None, expires_monotonic)
_cache: dict[tuple[str, str], tuple[str | None, float]] = {}


def _cache_get(user_id: UUID, key: str) -> tuple[bool, str | None]:
    entry = _cache.get((str(user_id), key))
    if entry is None:
        return False, None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        _cache.pop((str(user_id), key), None)
        return False, None
    return True, value


def _cache_put(user_id: UUID, key: str, value: str | None) -> None:
    _cache[(str(user_id), key)] = (value, time.monotonic() + CONSTANTS_CACHE_TTL)


def _cache_invalidate(user_id: UUID, key: str) -> None:
    _cache.pop((str(user_id), key), None)


def get_all_constants(*, session: Session, user_id: UUID) -> list[AppConstant]:
    return list(session.exec(select(AppConstant).where(AppConstant.user_id == user_id)).all())


def get_constant_value(*, session: Session, user_id: UUID, key: str) -> str | None:
    hit, cached = _cache_get(user_id, key)
    if hit:
        return cached

    row = session.exec(
        select(AppConstant)
        .where(AppConstant.user_id == user_id)
        .where(AppConstant.key == key)
    ).first()
    value = row.value if row else None
    _cache_put(user_id, key, value)
    return value


def upsert_constant(*, session: Session, user_id: UUID, key: str, value: str) -> AppConstant:
    row = session.exec(
        select(AppConstant)
        .where(AppConstant.user_id == user_id)
        .where(AppConstant.key == key)
    ).first()
    if row is None:
        row = AppConstant(user_id=user_id, key=key, value=value)
        session.add(row)
    else:
        row.value = value
        session.add(row)
    session.flush()
    session.refresh(row)
    _cache_invalidate(user_id, key)
    return row


def get_constant_decimal(
    *,
    session: Session,
    user_id: UUID,
    key: str,
    default: Decimal,
) -> Decimal:
    raw = get_constant_value(session=session, user_id=user_id, key=key)
    if raw is None:
        return default
    try:
        return Decimal(raw)
    except InvalidOperation:
        return default


def get_constant_int(
    *,
    session: Session,
    user_id: UUID,
    key: str,
    default: int,
) -> int:
    raw = get_constant_value(session=session, user_id=user_id, key=key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default
