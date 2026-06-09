from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlmodel import Session, select

from app.models.app_constant import AppConstant


def get_all_constants(*, session: Session, user_id: UUID) -> list[AppConstant]:
    return list(session.exec(select(AppConstant).where(AppConstant.user_id == user_id)).all())


def get_constant_value(*, session: Session, user_id: UUID, key: str) -> str | None:
    row = session.exec(
        select(AppConstant)
        .where(AppConstant.user_id == user_id)
        .where(AppConstant.key == key)
    ).first()
    return row.value if row else None


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
