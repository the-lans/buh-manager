from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, model_validator

_VALID_OPS = {"eq", "lt", "gt", "lte", "gte"}


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
        conditions = [
            self.cond_account_id,
            self.cond_day_month,
            self.cond_day_week,
            self.cond_amount,
            self.cond_type,
            self.cond_bank_category,
            self.cond_description,
        ]
        if all(c is None for c in conditions):
            raise ValueError("Необходимо указать хотя бы одно условие.")
        if self.cond_day_month is not None and self.cond_day_month_op not in _VALID_OPS:
            raise ValueError("cond_day_month_op must be one of: eq, lt, gt, lte, gte.")
        if self.cond_amount is not None and self.cond_amount_op not in _VALID_OPS:
            raise ValueError("cond_amount_op must be one of: eq, lt, gt, lte, gte.")
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


class ClassifierRuleApplyResult(BaseModel):
    updated_count: int
