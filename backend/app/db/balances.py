from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc
from sqlmodel import Session, col, func, select

from app.models.account import Account
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


def link_balances_to_document(
    *,
    session: Session,
    account_id: UUID,
    date_start: datetime,
    date_end: datetime,
    document_id: UUID,
) -> int:
    """Set document_id on balances in [date_start, date_end] that have no document yet."""
    rows = list(
        session.exec(
            select(Balance)
            .where(Balance.account_id == account_id)
            .where(Balance.recorded_at >= date_start)
            .where(Balance.recorded_at <= date_end)
            .where(col(Balance.document_id).is_(None))
        ).all()
    )
    for bal in rows:
        bal.document_id = document_id
        session.add(bal)
    return len(rows)


def get_balances_for_user(
    *,
    session: Session,
    user_id: UUID,
    account_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Balance]:
    """Return balances for all accounts owned by user, newest first."""
    query = (
        select(Balance)
        .join(Account, Balance.account_id == Account.id)  # type: ignore[arg-type]
        .where(Account.user_id == user_id)
    )
    if account_id is not None:
        query = query.where(Balance.account_id == account_id)
    query = query.order_by(desc(Balance.recorded_at)).offset(skip).limit(limit)  # type: ignore[arg-type]
    return list(session.exec(query).all())
