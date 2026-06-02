from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, col, select

from app.models.transaction import Transaction
from app.schemas.bank_statement import BalanceCheck


def verify_balance_chain(
    *,
    session: Session,
    account_id: UUID,
    period_start: datetime,
    period_end: datetime,
    opening_balance: Decimal | None,
    expected_closing: Decimal | None,
) -> BalanceCheck:
    transactions = list(
        session.exec(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .where(Transaction.occurred_at >= period_start)
            .where(Transaction.occurred_at <= period_end)
            .order_by(col(Transaction.occurred_at).asc(), col(Transaction.id).asc())
        ).all()
    )

    # Cannot compute chain when balance_after data is unavailable (TBank/Yandex)
    has_per_tx_balance = any(tx.balance_after is not None for tx in transactions)
    if not has_per_tx_balance or opening_balance is None:
        return BalanceCheck(
            is_available=False,
            opening_balance_statement=opening_balance,
            closing_balance_statement=expected_closing,
        )

    running = opening_balance
    for tx in transactions:
        running = running + tx.amount
        tx.calculated_balance_after = running
        tx.balance_mismatch = tx.balance_after is not None and tx.balance_after != running
        session.add(tx)

    closing_calculated = running
    discrepancy = (expected_closing - closing_calculated) if expected_closing is not None else None
    is_consistent = discrepancy == Decimal(0) if discrepancy is not None else None

    return BalanceCheck(
        is_available=True,
        opening_balance_statement=opening_balance,
        closing_balance_statement=expected_closing,
        closing_balance_calculated=closing_calculated,
        is_consistent=is_consistent,
        discrepancy=discrepancy,
    )
