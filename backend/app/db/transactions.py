from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, col, select

from app.constants import TX_DEDUP_WINDOW_SECONDS, ImportStatus, ReconciledStatus
from app.models.account import Account
from app.models.expense_type import ExpenseType
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionFilters, TransactionUpdate


def find_transaction_by_dedup_key(
    *,
    session: Session,
    account_id: UUID,
    occurred_at: datetime,
    balance_after: Decimal | None,
    amount: Decimal,
) -> tuple[Transaction | None, bool]:
    """
    Returns (transaction | None, used_fallback_key).
    Primary key: (account_id, occurred_at ± window, balance_after) — Sberbank-style.
    Fallback key: (account_id, occurred_at ± window, amount) — TBank/Yandex-style.
    """
    window = timedelta(seconds=TX_DEDUP_WINDOW_SECONDS)
    lower = occurred_at - window
    upper = occurred_at + window

    if balance_after is not None:
        result = session.exec(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .where(Transaction.occurred_at >= lower)
            .where(Transaction.occurred_at <= upper)
            .where(Transaction.balance_after == balance_after)
        ).first()
        return result, False

    # Fallback: match by amount when balance_after is unavailable
    result = session.exec(
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .where(Transaction.occurred_at >= lower)
        .where(Transaction.occurred_at <= upper)
        .where(Transaction.amount == amount)
    ).first()
    return result, True


def create_transaction(
    *,
    session: Session,
    account_id: UUID,
    occurred_at: datetime,
    amount: Decimal,
    type: str,
    processed_at: datetime | None = None,
    auth_code: str | None = None,
    bank_category: str | None = None,
    counterparty_id: str | None = None,
    expense_type_id: str | None = None,
    description: str | None = None,
    balance_after: Decimal | None = None,
    import_status: str = ImportStatus.IMPORTED,
    document_id: UUID | None = None,
) -> Transaction:
    transaction = Transaction(
        account_id=account_id,
        occurred_at=occurred_at,
        processed_at=processed_at,
        auth_code=auth_code,
        amount=amount,
        type=type,
        bank_category=bank_category,
        counterparty_id=counterparty_id,
        expense_type_id=expense_type_id,
        description=description,
        balance_after=balance_after,
        import_status=import_status,
        document_id=document_id,
    )
    session.add(transaction)
    session.flush()
    session.refresh(transaction)
    return transaction


def get_transaction_by_id(
    *,
    session: Session,
    transaction_id: UUID,
    user_id: UUID,
) -> Transaction | None:
    return session.exec(
        select(Transaction)
        .join(Account)
        .where(Transaction.id == transaction_id)
        .where(Account.user_id == user_id)
    ).first()


def get_transactions_for_user(
    *,
    session: Session,
    user_id: UUID,
    filters: TransactionFilters,
    skip: int = 0,
    limit: int = 100,
) -> list[Transaction]:
    query = select(Transaction).join(Account).where(Account.user_id == user_id)
    if filters.account_id is not None:
        query = query.where(Transaction.account_id == filters.account_id)
    if filters.start_date is not None:
        query = query.where(Transaction.occurred_at >= filters.start_date)
    if filters.end_date is not None:
        query = query.where(Transaction.occurred_at <= filters.end_date)
    if filters.type is not None:
        query = query.where(Transaction.type == filters.type)
    if filters.reconciled_status is not None:
        query = query.where(Transaction.reconciled_status == filters.reconciled_status)
    if filters.import_status is not None:
        query = query.where(Transaction.import_status == filters.import_status)
    query = query.order_by(col(Transaction.occurred_at).desc()).offset(skip).limit(limit)
    return list(session.exec(query).all())


def update_transaction(
    *,
    session: Session,
    transaction: Transaction,
    data: TransactionUpdate,
) -> Transaction:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(transaction, field, value)
    session.add(transaction)
    session.flush()
    session.refresh(transaction)
    return transaction


def delete_transaction(*, session: Session, transaction: Transaction) -> None:
    session.delete(transaction)


def get_unmatched_transactions_requiring_receipt(
    *,
    session: Session,
    user_id: UUID,
) -> list[Transaction]:
    return list(
        session.exec(
            select(Transaction)
            .join(Account)
            .join(ExpenseType, isouter=True)
            .where(Account.user_id == user_id)
            .where(col(Transaction.receipt_id).is_(None))
            .where(Transaction.reconciled_status == ReconciledStatus.UNMATCHED)
            .where(
                col(ExpenseType.receipt_required).is_(True)
                | col(Transaction.expense_type_id).is_(None)
            )
        ).all()
    )


def update_transaction_reconciled_status(
    *,
    session: Session,
    transaction: Transaction,
    reconciled_status: str,
) -> None:
    transaction.reconciled_status = reconciled_status
    session.add(transaction)


def update_transaction_receipt_link(
    *,
    session: Session,
    transaction: Transaction,
    receipt_id: UUID | None,
    reconciled_status: str,
) -> None:
    transaction.receipt_id = receipt_id
    transaction.reconciled_status = reconciled_status
    session.add(transaction)


def link_transactions_to_document(
    *,
    session: Session,
    account_id: UUID,
    user_id: UUID,
    date_start: datetime,
    date_end: datetime,
    document_id: UUID,
) -> int:
    """Set document_id on transactions in [date_start, date_end] that have no document yet."""
    rows = list(
        session.exec(
            select(Transaction)
            .join(Account)
            .where(Account.user_id == user_id)
            .where(Transaction.account_id == account_id)
            .where(Transaction.occurred_at >= date_start)
            .where(Transaction.occurred_at <= date_end)
            .where(col(Transaction.document_id).is_(None))
        ).all()
    )
    for tx in rows:
        tx.document_id = document_id
        session.add(tx)
    return len(rows)
