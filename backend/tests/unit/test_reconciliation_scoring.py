"""Unit tests for the reconciliation time-window and auto-match logic."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.constants import (
    RECONCILE_AUTO_MATCH_MAX_HOURS,
    ImportStatus,
    ReconciledStatus,
    TransactionType,
)
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.services.reconciliation import _in_time_window

BASE = datetime(2024, 6, 15, 12, 0)


def _tx(occurred_at: datetime, amount: Decimal = Decimal("-100")) -> Transaction:
    return Transaction(
        id=uuid4(),
        account_id=uuid4(),
        occurred_at=occurred_at,
        amount=amount,
        type=TransactionType.EXPENSE,
        expense_type_id="test-et",
        balance_after=None,
        reconciled_status=ReconciledStatus.UNMATCHED,
        import_status=ImportStatus.IMPORTED,
    )


def _receipt(paid_at: datetime, total: Decimal = Decimal("100")) -> Receipt:
    return Receipt(
        id=uuid4(),
        paid_at=paid_at,
        total_amount=total,
    )


# ── Auto-match time condition ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "delta_hours, expected_auto_match",
    [
        (0, True),
        (1, True),
        (11, True),   # just under limit
        (12, False),  # exactly at limit — not matched (strict less-than)
        (13, False),
    ],
)
def test_auto_match_time_condition(delta_hours: int, expected_auto_match: bool) -> None:
    time_diff_seconds = delta_hours * 3600
    assert (time_diff_seconds < RECONCILE_AUTO_MATCH_MAX_HOURS * 3600) is expected_auto_match


# ── Time window ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "offset_hours, expected_in_window",
    [
        (-11, True),   # 11h before paid_at → within PRE window (12h)
        (-13, False),  # 13h before → outside
        (0, True),     # same time
        (71, True),    # 71h after → within POST window (3 days = 72h)
        (73, False),   # 73h after → outside
    ],
)
def test_time_window(offset_hours: int, expected_in_window: bool) -> None:
    paid_at = BASE
    tx = _tx(paid_at + timedelta(hours=offset_hours))
    receipt = _receipt(paid_at)
    assert _in_time_window(tx=tx, receipt=receipt) is expected_in_window
