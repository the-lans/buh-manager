from datetime import datetime
from decimal import Decimal
import json
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.constants import TransactionType
from app.utils.dt import normalize_to_utc

_VALID_OPS = {"eq", "lt", "gt", "lte", "gte"}
_VALID_TX_TYPES = {tx_type.value for tx_type in TransactionType}


def _validate_classifier_conditions(
    *,
    cond_account_id: UUID | None,
    cond_day_month: int | None,
    cond_day_month_op: str | None,
    cond_day_week: str | None,
    cond_amount: Decimal | None,
    cond_amount_op: str | None,
    cond_type: str | None,
    cond_bank_category: str | None,
    cond_description: str | None,
) -> None:
    if cond_day_month is not None and not 1 <= cond_day_month <= 31:
        raise ValueError("cond_day_month must be between 1 and 31.")
    conditions = [
        cond_account_id,
        cond_day_month,
        cond_day_week,
        cond_amount,
        cond_type,
        cond_bank_category,
        cond_description,
    ]
    if all(c is None for c in conditions):
        raise ValueError("Необходимо указать хотя бы одно условие.")
    if cond_day_month is not None and cond_day_month_op not in _VALID_OPS:
        raise ValueError("cond_day_month_op must be one of: eq, lt, gt, lte, gte.")
    if cond_amount is not None and cond_amount_op not in _VALID_OPS:
        raise ValueError("cond_amount_op must be one of: eq, lt, gt, lte, gte.")
    if cond_type is not None and cond_type not in _VALID_TX_TYPES:
        raise ValueError("cond_type must be one of: EXPENSE, INCOME, TRANSFER.")
    if cond_day_week is not None:
        try:
            days = json.loads(cond_day_week)
        except (TypeError, ValueError) as err:
            raise ValueError("cond_day_week must be a JSON array of integers 0..6.") from err
        if not isinstance(days, list) or not days:
            raise ValueError("cond_day_week must be a non-empty JSON array of integers 0..6.")
        if any(not isinstance(day, int) or day < 0 or day > 6 for day in days):
            raise ValueError("cond_day_week must contain only integers 0..6.")


class ClassifierRuleCreate(BaseModel):
    name: str
    expense_type_id: str
    priority: int
    is_active: bool = True

    cond_account_id: UUID | None = None
    cond_day_month: int | None = None
    cond_day_month_op: str | None = None
    cond_day_week: str | None = None
    cond_amount: Decimal | None = None
    cond_amount_op: str | None = None
    cond_type: str | None = None
    cond_bank_category: str | None = None
    cond_description: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_conditions(self) -> "ClassifierRuleCreate":
        _validate_classifier_conditions(
            cond_account_id=self.cond_account_id,
            cond_day_month=self.cond_day_month,
            cond_day_month_op=self.cond_day_month_op,
            cond_day_week=self.cond_day_week,
            cond_amount=self.cond_amount,
            cond_amount_op=self.cond_amount_op,
            cond_type=self.cond_type,
            cond_bank_category=self.cond_bank_category,
            cond_description=self.cond_description,
        )
        return self


class ClassifierRuleUpdate(BaseModel):
    name: str | None = None
    expense_type_id: str | None = None
    priority: int | None = None
    is_active: bool | None = None

    cond_account_id: UUID | None = None
    cond_day_month: int | None = None
    cond_day_month_op: str | None = None
    cond_day_week: str | None = None
    cond_amount: Decimal | None = None
    cond_amount_op: str | None = None
    cond_type: str | None = None
    cond_bank_category: str | None = None
    cond_description: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_conditions(self) -> "ClassifierRuleUpdate":
        condition_fields = {
            "cond_account_id",
            "cond_day_month",
            "cond_day_month_op",
            "cond_day_week",
            "cond_amount",
            "cond_amount_op",
            "cond_type",
            "cond_bank_category",
            "cond_description",
        }
        if not (self.model_fields_set & condition_fields):
            return self

        _validate_classifier_conditions(
            cond_account_id=self.cond_account_id,
            cond_day_month=self.cond_day_month,
            cond_day_month_op=self.cond_day_month_op,
            cond_day_week=self.cond_day_week,
            cond_amount=self.cond_amount,
            cond_amount_op=self.cond_amount_op,
            cond_type=self.cond_type,
            cond_bank_category=self.cond_bank_category,
            cond_description=self.cond_description,
        )
        return self


class ClassifierRuleRead(BaseModel):
    id: UUID
    name: str
    expense_type_id: str
    priority: int
    is_active: bool
    representation: str

    cond_account_id: UUID | None
    cond_day_month: int | None
    cond_day_month_op: str | None
    cond_day_week: str | None
    cond_amount: Decimal | None
    cond_amount_op: str | None
    cond_type: str | None
    cond_bank_category: str | None
    cond_description: str | None

    model_config = {"from_attributes": True}


class ClassifierRuleApplyRequest(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_period(self) -> "ClassifierRuleApplyRequest":
        self.start_date = normalize_to_utc(self.start_date)
        self.end_date = normalize_to_utc(self.end_date)
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class ClassifierRuleApplyResult(BaseModel):
    updated_count: int
