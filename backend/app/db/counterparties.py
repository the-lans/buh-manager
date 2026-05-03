import re

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
) -> Counterparty:
    existing = session.exec(
        select(Counterparty).where(Counterparty.name == name)
    ).first()
    if existing is not None:
        return existing

    slug = _slug_from_name(name)
    # Ensure slug uniqueness
    base_slug = slug
    counter = 1
    while session.get(Counterparty, slug) is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1

    counterparty = Counterparty(id=slug, name=name, type=type)
    session.add(counterparty)
    session.commit()
    session.refresh(counterparty)
    return counterparty


def list_counterparties(*, session: Session) -> list[Counterparty]:
    return list(session.exec(select(Counterparty)).all())
