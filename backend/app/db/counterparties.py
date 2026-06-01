import re
from typing import Any

from sqlmodel import Session, select

from app.models.counterparty import Counterparty


def _slug_from_name(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    return slug[:64] or "unknown"


def get_counterparty_by_id(*, session: Session, counterparty_id: str) -> Counterparty | None:
    return session.get(Counterparty, counterparty_id)


def get_or_create_counterparty(
    *,
    session: Session,
    name: str,
    type: str = "STORE",
    inn: str | None = None,
    kpp: str | None = None,
) -> Counterparty:
    # Deduplicate by INN first (when provided)
    if inn is not None:
        existing_by_inn = session.exec(select(Counterparty).where(Counterparty.inn == inn)).first()
        if existing_by_inn is not None:
            return existing_by_inn

    existing_by_name = session.exec(select(Counterparty).where(Counterparty.name == name)).first()
    if existing_by_name is not None:
        return existing_by_name

    slug = _slug_from_name(name)
    base_slug = slug
    counter = 1
    while session.get(Counterparty, slug) is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1

    counterparty = Counterparty(id=slug, name=name, type=type, inn=inn, kpp=kpp)
    session.add(counterparty)
    session.flush()
    session.refresh(counterparty)
    return counterparty


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


def list_counterparties(*, session: Session) -> list[Counterparty]:
    return list(session.exec(select(Counterparty)).all())
