import re
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.counterparty import Counterparty
from app.utils.ids import scope_user_id


def _slug_from_name(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    return slug[:64] or "unknown"


def get_counterparty_by_id(
    *,
    session: Session,
    counterparty_id: str,
    user_id: UUID,
) -> Counterparty | None:
    scoped_id = scope_user_id(user_id=user_id, public_id=counterparty_id)
    result = session.exec(
        select(Counterparty)
        .where(Counterparty.id == scoped_id)
        .where(Counterparty.user_id == user_id)
    ).first()
    if result is not None:
        return result
    # Fallback: IDs created before scoping migration (stored without user prefix)
    return session.exec(
        select(Counterparty)
        .where(Counterparty.id == counterparty_id)
        .where(Counterparty.user_id == user_id)
    ).first()


def get_or_create_counterparty(
    *,
    session: Session,
    user_id: UUID,
    name: str,
    type: str = "STORE",
    inn: str | None = None,
    kpp: str | None = None,
) -> Counterparty:
    # Deduplicate by INN first (when provided)
    if inn is not None:
        existing_by_inn = session.exec(
            select(Counterparty)
            .where(Counterparty.user_id == user_id)
            .where(Counterparty.inn == inn)
        ).first()
        if existing_by_inn is not None:
            return existing_by_inn

    existing_by_name = session.exec(
        select(Counterparty).where(Counterparty.user_id == user_id).where(Counterparty.name == name)
    ).first()
    if existing_by_name is not None:
        return existing_by_name

    public_id = _slug_from_name(name)
    base_public_id = public_id
    counter = 1
    scoped_id = scope_user_id(user_id=user_id, public_id=public_id)
    while (
        session.exec(select(Counterparty).where(Counterparty.id == scoped_id)).first() is not None
    ):
        public_id = f"{base_public_id}-{counter}"
        scoped_id = scope_user_id(user_id=user_id, public_id=public_id)
        counter += 1

    counterparty = Counterparty(
        id=scoped_id,
        user_id=user_id,
        name=name,
        type=type,
        inn=inn,
        kpp=kpp,
    )
    try:
        # Use SAVEPOINT so a conflict rolls back only this insert,
        # leaving the outer transaction intact.
        with session.begin_nested():
            session.add(counterparty)
            session.flush()
        session.refresh(counterparty)
        return counterparty
    except IntegrityError:
        # Concurrent request won the race — look up the record it created.
        if inn is not None:
            existing = session.exec(
                select(Counterparty)
                .where(Counterparty.user_id == user_id)
                .where(Counterparty.inn == inn)
            ).first()
            if existing is not None:
                return existing
        existing = session.exec(
            select(Counterparty)
            .where(Counterparty.user_id == user_id)
            .where(Counterparty.name == name)
        ).first()
        if existing is not None:
            return existing
        raise


def update_counterparty(
    *,
    session: Session,
    counterparty: Counterparty,
    update_data: dict[str, Any],
) -> Counterparty:
    for field, value in update_data.items():
        setattr(counterparty, field, value)
    session.add(counterparty)
    session.flush()
    session.refresh(counterparty)
    return counterparty


def delete_counterparty(*, session: Session, counterparty: Counterparty) -> None:
    session.delete(counterparty)
    session.flush()


def list_counterparties(*, session: Session, user_id: UUID) -> list[Counterparty]:
    return list(session.exec(select(Counterparty).where(Counterparty.user_id == user_id)).all())
