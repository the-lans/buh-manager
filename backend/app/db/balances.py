from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, col, func, select

from app.constants import BalanceSource
from app.models.account import Account
from app.models.balance import Balance
from app.models.transaction import Transaction
from app.utils.dt import utcnow

# End of UTC day used as recorded_at for MANUAL calculated balances.
# Ensures idempotency: multiple runs on the same day hit the same (date, source) key.
_BALANCE_DAY_END_TIME: time = time(23, 59, 59)


def has_any_balance(*, session: Session, account_id: UUID) -> bool:
    count = session.exec(select(func.count()).where(Balance.account_id == account_id)).one()
    return count > 0


def get_accounts_with_balances(*, session: Session, account_ids: list[UUID]) -> set[UUID]:
    """Return the subset of account_ids that have at least one balance record."""
    if not account_ids:
        return set()
    rows = session.exec(
        select(Balance.account_id)
        .where(col(Balance.account_id).in_(account_ids))
        .distinct()
    ).all()
    return set(rows)


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
            select(Balance)
            .where(Balance.account_id == account_id)
            .order_by(col(Balance.recorded_at).asc())
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


def get_latest_balance_for_account(*, session: Session, account_id: UUID) -> Balance | None:
    """Return the most recent balance record for an account."""
    return session.exec(
        select(Balance)
        .where(Balance.account_id == account_id)
        .order_by(col(Balance.recorded_at).desc())
    ).first()


def calculate_balances_for_user(*, session: Session, user_id: UUID) -> list[Balance]:
    """Upsert a MANUAL balance for each account that has a known starting balance.

    The new amount is: latest_balance + SUM(transactions since latest_balance).
    Recorded at end-of-day UTC so repeated calls on the same day are idempotent.
    """
    today_end_utc = datetime.combine(utcnow().date(), _BALANCE_DAY_END_TIME)
    accounts: list[Account] = list(
        session.exec(select(Account).where(Account.user_id == user_id)).all()
    )
    results: list[Balance] = []

    for account in accounts:
        latest: Balance | None = get_latest_balance_for_account(
            session=session, account_id=account.id
        )
        if latest is None:
            continue

        tx_sum: Decimal | None = session.exec(
            select(func.sum(Transaction.amount))
            .where(Transaction.account_id == account.id)
            .where(Transaction.occurred_at > latest.recorded_at)
        ).one()

        new_amount: Decimal = latest.amount + (tx_sum or Decimal(0))

        if new_amount == latest.amount:
            continue

        balance: Balance = upsert_balance(
            session=session,
            account_id=account.id,
            amount=new_amount,
            recorded_at=today_end_utc,
            source=BalanceSource.MANUAL,
        )
        results.append(balance)

    return results


def get_balances_for_user(
    *,
    session: Session,
    user_id: UUID,
    account_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Balance]:
    """Return balances for all accounts owned by user, newest first."""
    query = select(Balance).join(Account).where(Account.user_id == user_id)
    if account_id is not None:
        query = query.where(Balance.account_id == account_id)
    query = query.order_by(col(Balance.recorded_at).desc()).offset(skip).limit(limit)
    return list(session.exec(query).all())
