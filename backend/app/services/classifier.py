from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING

from app.constants import ClassifierOp
from app.utils.dt import utc_to_app_timezone

if TYPE_CHECKING:
    from app.models.classifier_rule import ClassifierRule
    from app.models.transaction import Transaction

_DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]  # noqa: RUF001
_TYPE_LABELS = {"EXPENSE": "Расход", "INCOME": "Доход", "TRANSFER": "Перевод"}
_OP_SYMBOLS: dict[str, str] = {
    ClassifierOp.EQ: "=",
    ClassifierOp.LT: "<",
    ClassifierOp.GT: ">",
    ClassifierOp.LTE: "≤",
    ClassifierOp.GTE: "≥",
    ClassifierOp.BETWEEN: "≤…≤",
}


def _apply_op(value: Decimal, op: str, target: Decimal) -> bool:
    if op == ClassifierOp.EQ:
        return value == target
    if op == ClassifierOp.LT:
        return value < target
    if op == ClassifierOp.GT:
        return value > target
    if op == ClassifierOp.LTE:
        return value <= target
    if op == ClassifierOp.GTE:
        return value >= target
    return False


def match_transaction(tx: Transaction, rule: ClassifierRule) -> bool:
    tx_local_dt = utc_to_app_timezone(tx.occurred_at)

    if rule.cond_account_id is not None and tx.account_id != rule.cond_account_id:
        return False

    if rule.cond_day_month is not None:
        op = rule.cond_day_month_op or ClassifierOp.EQ
        day = Decimal(tx_local_dt.day)
        if op == ClassifierOp.BETWEEN:
            lo = Decimal(rule.cond_day_month)
            hi = Decimal(rule.cond_day_month_to) if rule.cond_day_month_to is not None else lo
            if not (lo <= day <= hi):
                return False
        elif not _apply_op(day, op, Decimal(rule.cond_day_month)):
            return False

    if rule.cond_day_week is not None:
        try:
            allowed_days: list[int] = json.loads(rule.cond_day_week)
        except (ValueError, TypeError):
            allowed_days = []
        if tx_local_dt.weekday() not in allowed_days:
            return False

    if rule.cond_amount is not None:
        op = rule.cond_amount_op or ClassifierOp.EQ
        if op == ClassifierOp.BETWEEN:
            lo = rule.cond_amount
            hi = rule.cond_amount_to if rule.cond_amount_to is not None else lo
            if not (lo <= tx.amount <= hi):
                return False
        elif not _apply_op(tx.amount, op, rule.cond_amount):
            return False

    if rule.cond_type is not None and tx.type != rule.cond_type:
        return False

    if rule.cond_bank_category is not None and (
        not tx.bank_category or rule.cond_bank_category.lower() not in tx.bank_category.lower()
    ):
        return False

    return not (
        rule.cond_description is not None
        and (not tx.description or rule.cond_description.lower() not in tx.description.lower())
    )


def apply_rules(rules: list[ClassifierRule], tx: Transaction) -> str | None:
    for rule in rules:
        if rule.is_active and match_transaction(tx, rule):
            return rule.expense_type_id
    return None


def generate_representation(
    *,
    cond_account_id: object = None,
    account_label: str | None = None,
    cond_day_month: int | None = None,
    cond_day_month_op: str | None = None,
    cond_day_month_to: int | None = None,
    cond_day_week: str | None = None,
    cond_amount: Decimal | None = None,
    cond_amount_op: str | None = None,
    cond_amount_to: Decimal | None = None,
    cond_type: str | None = None,
    cond_bank_category: str | None = None,
    cond_description: str | None = None,
) -> str:
    parts: list[str] = []

    if cond_account_id is not None:
        label = account_label or str(cond_account_id)
        parts.append(f"Счёт: {label}")

    if cond_day_month is not None:
        if cond_day_month_op == ClassifierOp.BETWEEN and cond_day_month_to is not None:
            parts.append(f"День месяца: {cond_day_month} ≤ ... ≤ {cond_day_month_to}")
        else:
            op_sym = _OP_SYMBOLS.get(cond_day_month_op or ClassifierOp.EQ, "=")
            parts.append(f"День месяца {op_sym} {cond_day_month}")

    if cond_day_week is not None:
        try:
            days = json.loads(cond_day_week)
            day_str = ", ".join(_DAY_NAMES[d] for d in days if 0 <= d <= 6)
        except (ValueError, TypeError):
            day_str = cond_day_week
        parts.append(f"День недели: {day_str}")

    if cond_amount is not None:
        if cond_amount_op == ClassifierOp.BETWEEN and cond_amount_to is not None:
            parts.append(f"Сумма: {cond_amount} ≤ ... ≤ {cond_amount_to}")
        else:
            op_sym = _OP_SYMBOLS.get(cond_amount_op or ClassifierOp.EQ, "=")
            parts.append(f"Сумма {op_sym} {cond_amount}")

    if cond_type is not None:
        parts.append(f"Тип: {_TYPE_LABELS.get(cond_type, cond_type)}")

    if cond_bank_category is not None:
        parts.append(f"Категория содержит '{cond_bank_category}'")

    if cond_description is not None:
        parts.append(f"Описание содержит '{cond_description}'")

    return "; ".join(parts) if parts else "—"
