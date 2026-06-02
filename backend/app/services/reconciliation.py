from collections import defaultdict
from datetime import timedelta
from decimal import Decimal  # noqa: TCH003
from uuid import uuid4

from rapidfuzz import fuzz
from sqlmodel import Session

from app.constants import (
    FUZZY_HIGH_THRESHOLD,
    FUZZY_LOW_THRESHOLD,
    RECONCILE_POST_WINDOW_DAYS,
    RECONCILE_PRE_WINDOW_HOURS,
    SCORE_FUZZY_HIGH,
    SCORE_FUZZY_LOW,
    SCORE_SINGLE_PAIR_BONUS,
    SCORE_THRESHOLD_AUTO,
    SCORE_TIME_UNDER_1H,
    SCORE_TIME_UNDER_3D,
    SCORE_TIME_UNDER_12H,
    ChangedBy,
    ReconciledStatus,
)
from app.db.receipts import get_unmatched_receipts
from app.db.reconciliation_reports import save_report
from app.db.transactions import (
    get_unmatched_transactions_requiring_receipt,
    update_transaction_receipt_link,
)
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.models.user import User
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


def _score_pair(
    *,
    tx: Transaction,
    receipt: Receipt,
    is_single_pair: bool,
) -> int:
    score = 0
    time_diff = abs((tx.occurred_at - receipt.paid_at).total_seconds())
    one_hour = 3600
    twelve_hours = 43200
    three_days = 259200

    if time_diff < one_hour:
        score += SCORE_TIME_UNDER_1H
    elif time_diff < twelve_hours:
        score += SCORE_TIME_UNDER_12H
    elif time_diff < three_days:
        score += SCORE_TIME_UNDER_3D

    tx_name = tx.counterparty_id or ""
    receipt_name = receipt.counterparty_id or ""
    if tx_name and receipt_name:
        ratio = fuzz.token_set_ratio(tx_name, receipt_name)
        if ratio > FUZZY_HIGH_THRESHOLD:
            score += SCORE_FUZZY_HIGH
        elif ratio > FUZZY_LOW_THRESHOLD:
            score += SCORE_FUZZY_LOW

    if is_single_pair:
        score += SCORE_SINGLE_PAIR_BONUS

    return score


def _in_time_window(*, tx: Transaction, receipt: Receipt) -> bool:
    pre = timedelta(hours=RECONCILE_PRE_WINDOW_HOURS)
    post = timedelta(days=RECONCILE_POST_WINDOW_DAYS)
    lower = receipt.paid_at - pre
    upper = receipt.paid_at + post
    return lower <= tx.occurred_at <= upper


def run_reconciliation(
    *,
    session: Session,
    current_user: User,
) -> ReconciliationReport:
    transactions = get_unmatched_transactions_requiring_receipt(
        session=session, user_id=current_user.id
    )
    receipts = get_unmatched_receipts(session=session, user_id=current_user.id)

    # Partition by amount (absolute value for expenses)
    tx_buckets: dict[Decimal, list[Transaction]] = defaultdict(list)
    for tx in transactions:
        tx_buckets[abs(tx.amount)].append(tx)

    receipt_buckets: dict[Decimal, list[Receipt]] = defaultdict(list)
    for receipt in receipts:
        receipt_buckets[abs(receipt.total_amount)].append(receipt)

    auto_matched = 0
    collisions: list[CollisionGroup] = []
    missing_receipts: list[MissingReceiptItem] = []
    unmatched_receipts: list[UnmatchedReceiptItem] = []

    all_amounts = set(tx_buckets.keys()) | set(receipt_buckets.keys())

    for amount in all_amounts:
        bucket_txs = tx_buckets.get(amount, [])
        bucket_receipts = receipt_buckets.get(amount, [])

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
                        counterparty_id=tx.counterparty_id,
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
                        counterparty_id=tx.counterparty_id,
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
            # N:M collision — only among items that actually fall within the time window
            collision_id = str(uuid4())
            collisions.append(
                CollisionGroup(
                    collision_id=collision_id,
                    amount=amount,
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
                            counterparty_id=tx.counterparty_id,
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

        score = _score_pair(tx=tx, receipt=receipt, is_single_pair=True)
        if score >= SCORE_THRESHOLD_AUTO:
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
                    counterparty_id=tx.counterparty_id,
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
