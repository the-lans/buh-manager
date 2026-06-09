from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.app_constant import AppConstant
from app.utils.ttl_cache import TTLCache

CONSTANTS_CACHE_TTL: float = 10.0

# (str(user_id), key) -> value | None
_cache: TTLCache[tuple[str, str], str | None] = TTLCache(ttl=CONSTANTS_CACHE_TTL)


def invalidate_constant_cache(user_id: UUID, key: str) -> None:
    """Evict a single entry from the in-process cache. Call after a successful commit."""
    _cache.invalidate((str(user_id), key))


def get_all_constants(*, session: Session, user_id: UUID) -> list[AppConstant]:
    return list(session.exec(select(AppConstant).where(AppConstant.user_id == user_id)).all())


def get_constant_value(*, session: Session, user_id: UUID, key: str) -> str | None:
    cache_key = (str(user_id), key)
    hit, cached = _cache.get(cache_key)
    if hit:
        return cached

    row = session.exec(
        select(AppConstant)
        .where(AppConstant.user_id == user_id)
        .where(AppConstant.key == key)
    ).first()
    value = row.value if row else None
    _cache.put(cache_key, value)
    return value


def upsert_constant(*, session: Session, user_id: UUID, key: str, value: str) -> AppConstant:
    """
    Insert or update a constant. Does NOT touch the cache — caller must call
    invalidate_constant_cache(user_id, key) after the surrounding transaction commits.
    """
    row = session.exec(
        select(AppConstant)
        .where(AppConstant.user_id == user_id)
        .where(AppConstant.key == key)
    ).first()

    if row is not None:
        row.value = value
        session.add(row)
        session.flush()
        session.refresh(row)
        return row

    # First insert — use SAVEPOINT to survive a concurrent insert race.
    new_row = AppConstant(user_id=user_id, key=key, value=value)
    try:
        with session.begin_nested():
            session.add(new_row)
            session.flush()
        session.refresh(new_row)
        return new_row
    except IntegrityError:
        # Concurrent request inserted first — fetch that row and update it.
        row = session.exec(
            select(AppConstant)
            .where(AppConstant.user_id == user_id)
            .where(AppConstant.key == key)
        ).first()
        if row is None:
            raise
        row.value = value
        session.add(row)
        session.flush()
        session.refresh(row)
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
