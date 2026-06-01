from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, func, select

from app.models.balance import Balance


def has_any_balance(*, session: Session, account_id: UUID) -> bool:
    count = session.exec(select(func.count()).where(Balance.account_id == account_id)).one()
    return count > 0


def upsert_balance(
    *,
    session: Session,
    account_id: UUID,
    amount: Decimal,
    recorded_at: datetime,
    source: str,
    document_id: UUID | None = None,
) -> Balance:
    existing = session.exec(
        select(Balance)
        .where(Balance.account_id == account_id)
        .where(Balance.recorded_at == recorded_at)
        .where(Balance.source == source)
    ).first()

    if existing is not None:
        existing.amount = amount
        if document_id is not None:
            existing.document_id = document_id
        session.add(existing)
        session.flush()
        session.refresh(existing)
        return existing

    balance = Balance(
        account_id=account_id,
        amount=amount,
        recorded_at=recorded_at,
        source=source,
        document_id=document_id,
    )
    session.add(balance)
    session.flush()
    session.refresh(balance)
    return balance


def get_balances_for_account(*, session: Session, account_id: UUID) -> list[Balance]:
    return list(
        session.exec(
            select(Balance).where(Balance.account_id == account_id).order_by(Balance.recorded_at)  # type: ignore[arg-type]
        ).all()
    )
