from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from app.constants import (
    RECONCILE_AMOUNT_TOLERANCE,
    RECONCILE_AUTO_MATCH_MAX_HOURS,
    RECONCILE_POST_WINDOW_DAYS,
    RECONCILE_PRE_WINDOW_HOURS,
    ChangedBy,
    ReconciledStatus,
)
from app.db.app_constants import get_constant_decimal, get_constant_int
from app.db.receipts import get_unmatched_receipts
from app.db.reconciliation_reports import save_report
from app.db.transactions import (
    get_unmatched_transactions_requiring_receipt,
    update_transaction_receipt_link,
)
from app.schemas.reconciliation import (
    CollisionGroup,
    CollisionReceiptItem,
    CollisionTransactionItem,
    MissingReceiptItem,
    ReconciliationReport,
    ReconciliationSummary,
    UnmatchedReceiptItem,
)
from app.services.audit import audit_match
from app.utils.dt import utcnow

if TYPE_CHECKING:
    from decimal import Decimal

    from sqlmodel import Session

    from app.models.receipt import Receipt
    from app.models.transaction import Transaction
    from app.models.user import User


def _in_time_window(*, tx: Transaction, receipt: Receipt) -> bool:
    pre = timedelta(hours=RECONCILE_PRE_WINDOW_HOURS)
    post = timedelta(days=RECONCILE_POST_WINDOW_DAYS)
    lower = receipt.paid_at - pre
    upper = receipt.paid_at + post
    return lower <= tx.occurred_at <= upper


def _amounts_match(tx: Transaction, receipt: Receipt, *, tolerance: Decimal) -> bool:
    return abs(abs(tx.amount) - abs(receipt.total_amount)) <= tolerance


def _build_amount_groups(
    transactions: list[Transaction],
    receipts: list[Receipt],
    *,
    tolerance: Decimal,
) -> list[tuple[list[Transaction], list[Receipt]]]:
    """
    Group transactions and receipts into amount-compatible clusters using union-find.
    Supports arbitrary tolerance: items are in the same cluster if their amounts
    are within tolerance of each other.
    """
    n_tx = len(transactions)
    parent = list(range(n_tx + len(receipts)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    for i, tx in enumerate(transactions):
        for j, receipt in enumerate(receipts):
            if _amounts_match(tx, receipt, tolerance=tolerance):
                union(i, n_tx + j)

    groups: dict[int, tuple[list[Transaction], list[Receipt]]] = {}
    for i, tx in enumerate(transactions):
        root = find(i)
        if root not in groups:
            groups[root] = ([], [])
        groups[root][0].append(tx)
    for j, receipt in enumerate(receipts):
        root = find(n_tx + j)
        if root not in groups:
            groups[root] = ([], [])
        groups[root][1].append(receipt)

    return list(groups.values())


def run_reconciliation(
    *,
    session: Session,
    current_user: User,
) -> ReconciliationReport:
    tolerance = get_constant_decimal(
        session=session,
        user_id=current_user.id,
        key="RECONCILE_AMOUNT_TOLERANCE",
        default=RECONCILE_AMOUNT_TOLERANCE,
    )
    auto_match_hours = get_constant_int(
        session=session,
        user_id=current_user.id,
        key="RECONCILE_AUTO_MATCH_MAX_HOURS",
        default=RECONCILE_AUTO_MATCH_MAX_HOURS,
    )

    transactions = get_unmatched_transactions_requiring_receipt(
        session=session, user_id=current_user.id
    )
    receipts = get_unmatched_receipts(session=session, user_id=current_user.id)

    auto_matched = 0
    collisions: list[CollisionGroup] = []
    missing_receipts: list[MissingReceiptItem] = []
    unmatched_receipts: list[UnmatchedReceiptItem] = []

    for bucket_txs, bucket_receipts in _build_amount_groups(transactions, receipts, tolerance=tolerance):
        if not bucket_txs:
            for r in bucket_receipts:
                unmatched_receipts.append(
                    UnmatchedReceiptItem(
                        receipt_id=r.id,
                        paid_at=r.paid_at,
                        total_amount=r.total_amount,
                        counterparty_id=r.counterparty_id,
                    )
                )
            continue

        if not bucket_receipts:
            for tx in bucket_txs:
                missing_receipts.append(
                    MissingReceiptItem(
                        transaction_id=tx.id,
                        occurred_at=tx.occurred_at,
                        amount=tx.amount,
                        expense_type_id=tx.expense_type_id,
                    )
                )
            continue

        # Apply time window filter: only pairs where tx falls inside receipt's window
        filtered_pairs: list[tuple[Transaction, Receipt]] = [
            (tx, r)
            for tx in bucket_txs
            for r in bucket_receipts
            if _in_time_window(tx=tx, receipt=r)
        ]

        # Separate items that have at least one valid partner from those that don't
        tx_ids_in_window = {tx.id for tx, _ in filtered_pairs}
        receipt_ids_in_window = {r.id for _, r in filtered_pairs}

        txs_in_window = [tx for tx in bucket_txs if tx.id in tx_ids_in_window]
        receipts_in_window = [r for r in bucket_receipts if r.id in receipt_ids_in_window]

        for tx in bucket_txs:
            if tx.id not in tx_ids_in_window:
                missing_receipts.append(
                    MissingReceiptItem(
                        transaction_id=tx.id,
                        occurred_at=tx.occurred_at,
                        amount=tx.amount,
                        expense_type_id=tx.expense_type_id,
                    )
                )
        for r in bucket_receipts:
            if r.id not in receipt_ids_in_window:
                unmatched_receipts.append(
                    UnmatchedReceiptItem(
                        receipt_id=r.id,
                        paid_at=r.paid_at,
                        total_amount=r.total_amount,
                        counterparty_id=r.counterparty_id,
                    )
                )

        if not txs_in_window or not receipts_in_window:
            continue

        if len(txs_in_window) > 1 or len(receipts_in_window) > 1:
            collision_id = str(uuid4())
            collisions.append(
                CollisionGroup(
                    collision_id=collision_id,
                    amount=bucket_txs[0].amount,
                    reason="MULTIPLE_MATCHES",
                    message=(
                        f"Найдено {len(txs_in_window)} транзакции и "
                        f"{len(receipts_in_window)} чека на одинаковую сумму. "
                        "Требуется ручное сопоставление."
                    ),
                    involved_transactions=[
                        CollisionTransactionItem(
                            id=tx.id,
                            occurred_at=tx.occurred_at,
                            amount=tx.amount,
                        )
                        for tx in txs_in_window
                    ],
                    involved_receipts=[
                        CollisionReceiptItem(
                            id=r.id,
                            paid_at=r.paid_at,
                            counterparty_id=r.counterparty_id,
                            total_amount=r.total_amount,
                        )
                        for r in receipts_in_window
                    ],
                )
            )
            continue

        # 1:1 case: exactly one tx and one receipt within the time window
        tx = txs_in_window[0]
        receipt = receipts_in_window[0]

        time_diff = abs((tx.occurred_at - receipt.paid_at).total_seconds())
        if time_diff < auto_match_hours * 3600:
            update_transaction_receipt_link(
                session=session,
                transaction=tx,
                receipt_id=receipt.id,
                reconciled_status=ReconciledStatus.MATCHED,
            )
            audit_match(
                session=session,
                transaction_id=tx.id,
                receipt_id=receipt.id,
                changed_by=ChangedBy.AGENT,
                user_id=current_user.id,
            )
            auto_matched += 1
        else:
            missing_receipts.append(
                MissingReceiptItem(
                    transaction_id=tx.id,
                    occurred_at=tx.occurred_at,
                    amount=tx.amount,
                    expense_type_id=tx.expense_type_id,
                )
            )
            unmatched_receipts.append(
                UnmatchedReceiptItem(
                    receipt_id=receipt.id,
                    paid_at=receipt.paid_at,
                    total_amount=receipt.total_amount,
                    counterparty_id=receipt.counterparty_id,
                )
            )

    session.commit()

    report = ReconciliationReport(
        report_generated_at=utcnow(),
        summary=ReconciliationSummary(
            auto_matched_count=auto_matched,
            missing_receipts_count=len(missing_receipts),
            unmatched_receipts_count=len(unmatched_receipts),
            collisions_count=len(collisions),
        ),
        collisions=collisions,
        missing_receipts=missing_receipts,
        unmatched_receipts=unmatched_receipts,
    )

    save_report(
        session=session,
        user_id=current_user.id,
        report_data=report.model_dump(),
    )
    session.commit()

    return report
