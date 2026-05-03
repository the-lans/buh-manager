from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.constants import ImportStatus, ReconciledStatus, TransactionType
from app.models.transaction import Transaction
from app.services.balance_chain import verify_balance_chain


def _make_tx(
    account_id: object,
    occurred_at: datetime,
    amount: Decimal,
    balance_after: Decimal | None = None,
) -> Transaction:
    return Transaction(
        id=uuid4(),
        account_id=account_id,  # type: ignore[arg-type]
        occurred_at=occurred_at,
        amount=amount,
        type=TransactionType.EXPENSE,
        balance_after=balance_after,
        reconciled_status=ReconciledStatus.UNMATCHED,
        import_status=ImportStatus.IMPORTED,
    )


BASE = datetime(2024, 1, 1, 12, 0)
START = datetime(2024, 1, 1, 0, 0)
END = datetime(2024, 1, 31, 23, 59)


@pytest.mark.parametrize(
    "opening, txs_amounts_balances, expected_closing, expect_consistent",
    [
        # (a) clean chain — is_consistent=True
        (
            Decimal("1000"),
            [(Decimal("-100"), Decimal("900")), (Decimal("-200"), Decimal("700"))],
            Decimal("700"),
            True,
        ),
        # (e) closing discrepancy
        (
            Decimal("1000"),
            [(Decimal("-100"), Decimal("900"))],
            Decimal("500"),  # wrong expected closing
            False,
        ),
    ],
)
def test_balance_chain_consistency(
    session: Session,
    test_account: object,
    opening: Decimal,
    txs_amounts_balances: list[tuple[Decimal, Decimal]],
    expected_closing: Decimal,
    expect_consistent: bool,
) -> None:
    acc_id = test_account.id
    for i, (amt, bal) in enumerate(txs_amounts_balances):
        tx = _make_tx(acc_id, BASE + timedelta(hours=i), amt, bal)
        session.add(tx)
    session.commit()

    result = verify_balance_chain(
        session=session,
        account_id=acc_id,
        period_start=START,
        period_end=END,
        opening_balance=opening,
        expected_closing=expected_closing,
    )

    assert result.is_available is True
    assert result.is_consistent is expect_consistent


def test_balance_chain_marks_mismatch(session: Session, test_account: object) -> None:
    acc_id = test_account.id
    # Opening 1000, tx -100 → should be 900; put 999 as balance_after → mismatch
    tx = _make_tx(acc_id, BASE, Decimal("-100"), Decimal("999"))
    session.add(tx)
    session.commit()

    verify_balance_chain(
        session=session,
        account_id=acc_id,
        period_start=START,
        period_end=END,
        opening_balance=Decimal("1000"),
        expected_closing=None,
    )
    session.flush()
    session.refresh(tx)
    assert tx.balance_mismatch is True
    assert tx.calculated_balance_after == Decimal("900")


def test_balance_chain_no_transactions(session: Session, test_account: object) -> None:
    acc_id = test_account.id
    result = verify_balance_chain(
        session=session,
        account_id=acc_id,
        period_start=START,
        period_end=END,
        opening_balance=Decimal("500"),
        expected_closing=Decimal("500"),
    )
    # No transactions but opening_balance provided; is_available=False because no per-tx balance
    assert result.is_available is False


def test_balance_chain_unavailable_when_no_balance_after(
    session: Session, test_account: object
) -> None:
    acc_id = test_account.id
    tx = _make_tx(acc_id, BASE, Decimal("-50"), balance_after=None)
    session.add(tx)
    session.commit()

    result = verify_balance_chain(
        session=session,
        account_id=acc_id,
        period_start=START,
        period_end=END,
        opening_balance=Decimal("1000"),
        expected_closing=Decimal("950"),
    )
    assert result.is_available is False


def test_balance_chain_unavailable_when_opening_missing(
    session: Session, test_account: object
) -> None:
    acc_id = test_account.id
    tx = _make_tx(acc_id, BASE, Decimal("-50"), balance_after=Decimal("950"))
    session.add(tx)
    session.commit()

    result = verify_balance_chain(
        session=session,
        account_id=acc_id,
        period_start=START,
        period_end=END,
        opening_balance=None,
        expected_closing=Decimal("950"),
    )
    assert result.is_available is False
