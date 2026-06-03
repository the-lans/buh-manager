"""Unit tests for the reconciliation scoring and time-window logic."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.constants import (
    SCORE_SINGLE_PAIR_BONUS,
    SCORE_THRESHOLD_AUTO,
    SCORE_TIME_UNDER_1H,
    SCORE_TIME_UNDER_3D,
    SCORE_TIME_UNDER_12H,
    ImportStatus,
    ReconciledStatus,
    TransactionType,
)
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.services.reconciliation import _in_time_window, _score_pair

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


# ── Time scoring ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "delta_seconds, expected_time_score",
    [
        (600, SCORE_TIME_UNDER_1H),  # 10 min → <1h
        (3599, SCORE_TIME_UNDER_1H),  # just under 1h
        (3601, SCORE_TIME_UNDER_12H),  # just over 1h → <12h
        (43199, SCORE_TIME_UNDER_12H),  # just under 12h
        (43201, SCORE_TIME_UNDER_3D),  # just over 12h → <3d
        (259199, SCORE_TIME_UNDER_3D),  # just under 3d
        (259201, 0),  # over 3d → 0 time score
    ],
)
def test_time_score_brackets(delta_seconds: int, expected_time_score: int) -> None:
    tx = _tx(BASE)
    receipt = _receipt(BASE + timedelta(seconds=delta_seconds))
    score = _score_pair(tx=tx, receipt=receipt, is_single_pair=False)
    assert score == expected_time_score


def test_single_pair_bonus_added() -> None:
    tx = _tx(BASE)
    receipt = _receipt(BASE + timedelta(minutes=5))
    score_single = _score_pair(tx=tx, receipt=receipt, is_single_pair=True)
    score_multi = _score_pair(tx=tx, receipt=receipt, is_single_pair=False)
    assert score_single - score_multi == SCORE_SINGLE_PAIR_BONUS


def test_auto_match_threshold_reached() -> None:
    # <1h (40) + single pair bonus (20) = 60 ≥ 55 → auto-matched
    tx = _tx(BASE)
    receipt = _receipt(BASE + timedelta(minutes=5))
    score = _score_pair(tx=tx, receipt=receipt, is_single_pair=True)
    assert score >= SCORE_THRESHOLD_AUTO


# ── Time window ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "offset_hours, expected_in_window",
    [
        (-11, True),  # 11h before paid_at → within PRE window (12h)
        (-13, False),  # 13h before → outside
        (0, True),  # same time
        (71, True),  # 71h after → within POST window (3 days = 72h)
        (73, False),  # 73h after → outside
    ],
)
def test_time_window(offset_hours: int, expected_in_window: bool) -> None:
    paid_at = BASE
    tx = _tx(paid_at + timedelta(hours=offset_hours))
    receipt = _receipt(paid_at)
    assert _in_time_window(tx=tx, receipt=receipt) is expected_in_window
