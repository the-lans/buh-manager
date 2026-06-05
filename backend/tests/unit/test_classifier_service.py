"""Unit tests for classifier rule matching and representation generation."""

import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.constants import ImportStatus, ReconciledStatus, TransactionType
from app.models.classifier_rule import ClassifierRule
from app.models.transaction import Transaction
from app.services.classifier import apply_rules, generate_representation, match_transaction

ACCOUNT_ID = uuid4()
OTHER_ACCOUNT_ID = uuid4()

# Monday 2026-06-01 10:00 UTC
BASE_DT = datetime(2026, 6, 1, 10, 0)  # weekday() == 0 (Mon), day == 1


def _tx(
    *,
    account_id=ACCOUNT_ID,
    occurred_at: datetime = BASE_DT,
    amount: Decimal = Decimal("-500.00"),
    type: str = TransactionType.EXPENSE,
    bank_category: str | None = "Продукты",
    description: str | None = "Покупка продуктов",
) -> Transaction:
    return Transaction(
        id=uuid4(),
        account_id=account_id,
        occurred_at=occurred_at,
        amount=amount,
        type=type,
        bank_category=bank_category,
        expense_type_id="et-default",
        description=description,
        reconciled_status=ReconciledStatus.UNMATCHED,
        import_status=ImportStatus.IMPORTED,
    )


def _rule(**kwargs) -> ClassifierRule:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        name="Тест",
        expense_type_id="et-rule",
        priority=1,
        is_active=True,
        representation="",
        cond_account_id=None,
        cond_day_month=None,
        cond_day_month_op=None,
        cond_day_week=None,
        cond_amount=None,
        cond_amount_op=None,
        cond_type=None,
        cond_bank_category=None,
        cond_description=None,
    )
    defaults.update(kwargs)
    return ClassifierRule(**defaults)


# ── account_id ────────────────────────────────────────────────────────────────


def test_match_account_id_matches() -> None:
    tx = _tx(account_id=ACCOUNT_ID)
    rule = _rule(cond_account_id=ACCOUNT_ID)
    assert match_transaction(tx, rule) is True


def test_match_account_id_no_match() -> None:
    tx = _tx(account_id=ACCOUNT_ID)
    rule = _rule(cond_account_id=OTHER_ACCOUNT_ID)
    assert match_transaction(tx, rule) is False


# ── day_month ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "op, day, tx_day, expected",
    [
        ("eq", 1, 1, True),
        ("eq", 1, 2, False),
        ("lt", 15, 10, True),
        ("lt", 15, 15, False),
        ("lte", 15, 15, True),
        ("gt", 10, 15, True),
        ("gt", 10, 10, False),
        ("gte", 10, 10, True),
    ],
)
def test_match_day_month(op: str, day: int, tx_day: int, expected: bool) -> None:
    tx = _tx(occurred_at=datetime(2026, 6, tx_day, 12, 0))
    rule = _rule(cond_day_month=day, cond_day_month_op=op)
    assert match_transaction(tx, rule) is expected


# ── day_week ──────────────────────────────────────────────────────────────────


def test_match_day_week_hit() -> None:
    # BASE_DT is Monday (weekday=0)
    tx = _tx(occurred_at=BASE_DT)
    rule = _rule(cond_day_week=json.dumps([0, 2, 4]))  # Mon, Wed, Fri
    assert match_transaction(tx, rule) is True


def test_match_day_week_miss() -> None:
    # BASE_DT is Monday (weekday=0)
    tx = _tx(occurred_at=BASE_DT)
    rule = _rule(cond_day_week=json.dumps([1, 3, 5]))  # Tue, Thu, Sat
    assert match_transaction(tx, rule) is False


def test_match_day_month_uses_app_timezone() -> None:
    # 2026-02-28 21:30 UTC == 2026-03-01 00:30 Europe/Moscow
    tx = _tx(occurred_at=datetime(2026, 2, 28, 21, 30))
    rule = _rule(cond_day_month=1, cond_day_month_op="eq")
    assert match_transaction(tx, rule) is True


def test_match_day_week_uses_app_timezone() -> None:
    # 2026-02-28 21:30 UTC == Sunday 2026-03-01 00:30 Europe/Moscow
    tx = _tx(occurred_at=datetime(2026, 2, 28, 21, 30))
    rule = _rule(cond_day_week=json.dumps([6]))  # Sunday
    assert match_transaction(tx, rule) is True


# ── amount ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "op, threshold, tx_amount, expected",
    [
        ("eq", Decimal("-500"), Decimal("-500"), True),   # -500 == -500 → True
        ("eq", Decimal("-500"), Decimal("-400"), False),  # -400 == -500 → False
        ("lt", Decimal("-300"), Decimal("-500"), True),   # -500 < -300 → True (more negative)
        ("lt", Decimal("-600"), Decimal("-500"), False),  # -500 < -600 → False
        ("gt", Decimal("-600"), Decimal("-500"), True),   # -500 > -600 → True
        ("gt", Decimal("-400"), Decimal("-500"), False),  # -500 > -400 → False
        ("lte", Decimal("-500"), Decimal("-500"), True),  # -500 <= -500 → True
        ("gte", Decimal("-300"), Decimal("-500"), False), # -500 >= -300 → False
        ("gte", Decimal("-600"), Decimal("-500"), True),  # -500 >= -600 → True
    ],
)
def test_match_amount(op: str, threshold: Decimal, tx_amount: Decimal, expected: bool) -> None:
    tx = _tx(amount=tx_amount)
    rule = _rule(cond_amount=threshold, cond_amount_op=op)
    assert match_transaction(tx, rule) is expected


# ── type ──────────────────────────────────────────────────────────────────────


def test_match_type_matches() -> None:
    tx = _tx(type=TransactionType.EXPENSE)
    rule = _rule(cond_type="EXPENSE")
    assert match_transaction(tx, rule) is True


def test_match_type_no_match() -> None:
    tx = _tx(type=TransactionType.INCOME)
    rule = _rule(cond_type="EXPENSE")
    assert match_transaction(tx, rule) is False


# ── bank_category ─────────────────────────────────────────────────────────────


def test_match_bank_category_substring() -> None:
    tx = _tx(bank_category="Продукты питания")
    rule = _rule(cond_bank_category="продукты")  # case-insensitive
    assert match_transaction(tx, rule) is True


def test_match_bank_category_no_match() -> None:
    tx = _tx(bank_category="Рестораны")
    rule = _rule(cond_bank_category="продукты")
    assert match_transaction(tx, rule) is False


def test_match_bank_category_null_tx() -> None:
    tx = _tx(bank_category=None)
    rule = _rule(cond_bank_category="продукты")
    assert match_transaction(tx, rule) is False


# ── description ───────────────────────────────────────────────────────────────


def test_match_description_substring() -> None:
    tx = _tx(description="Покупка продуктов в магазине")
    rule = _rule(cond_description="ПРОДУКТОВ")  # case-insensitive
    assert match_transaction(tx, rule) is True


def test_match_description_null_tx() -> None:
    tx = _tx(description=None)
    rule = _rule(cond_description="продукт")
    assert match_transaction(tx, rule) is False


# ── multiple conditions ───────────────────────────────────────────────────────


def test_match_multiple_conditions_all_match() -> None:
    tx = _tx(type=TransactionType.EXPENSE, bank_category="Продукты")
    rule = _rule(cond_type="EXPENSE", cond_bank_category="продукты")
    assert match_transaction(tx, rule) is True


def test_match_multiple_conditions_one_fails() -> None:
    tx = _tx(type=TransactionType.INCOME, bank_category="Продукты")
    rule = _rule(cond_type="EXPENSE", cond_bank_category="продукты")
    assert match_transaction(tx, rule) is False


# ── apply_rules ───────────────────────────────────────────────────────────────


def test_apply_rules_returns_first_match() -> None:
    tx = _tx(type=TransactionType.EXPENSE)
    rule1 = _rule(priority=1, expense_type_id="et-high", cond_type="EXPENSE")
    rule2 = _rule(priority=2, expense_type_id="et-low", cond_type="EXPENSE")
    result = apply_rules([rule1, rule2], tx)
    assert result == "et-high"


def test_apply_rules_skips_inactive() -> None:
    tx = _tx(type=TransactionType.EXPENSE)
    rule1 = _rule(priority=1, expense_type_id="et-inactive", cond_type="EXPENSE", is_active=False)
    rule2 = _rule(priority=2, expense_type_id="et-active", cond_type="EXPENSE", is_active=True)
    result = apply_rules([rule1, rule2], tx)
    assert result == "et-active"


def test_apply_rules_no_match_returns_none() -> None:
    tx = _tx(type=TransactionType.INCOME)
    rule = _rule(cond_type="EXPENSE")
    result = apply_rules([rule], tx)
    assert result is None


def test_apply_rules_empty_rules() -> None:
    tx = _tx()
    assert apply_rules([], tx) is None


# ── generate_representation ───────────────────────────────────────────────────


def test_generate_representation_type_only() -> None:
    rep = generate_representation(cond_type="EXPENSE")
    assert rep == "Тип: Расход"


def test_generate_representation_amount_with_op() -> None:
    rep = generate_representation(cond_amount=Decimal("1000"), cond_amount_op="gte")
    assert "≥" in rep
    assert "1000" in rep


def test_generate_representation_day_week() -> None:
    rep = generate_representation(cond_day_week=json.dumps([0, 4]))
    assert "Пн" in rep
    assert "Пт" in rep


def test_generate_representation_substrings() -> None:
    rep = generate_representation(cond_bank_category="кофе", cond_description="завтрак")
    assert "'кофе'" in rep
    assert "'завтрак'" in rep


def test_generate_representation_empty() -> None:
    rep = generate_representation()
    assert rep == "—"


def test_generate_representation_account_label() -> None:
    rep = generate_representation(cond_account_id=uuid4(), account_label="Сбербанк ***1234")
    assert "Сбербанк ***1234" in rep


def test_generate_representation_day_month_with_op() -> None:
    rep = generate_representation(cond_day_month=15, cond_day_month_op="lte")
    assert "≤" in rep
    assert "15" in rep
