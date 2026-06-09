import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from app.constants import ClassifierOp, TransactionType
from app.utils.dt import normalize_to_utc

_VALID_OPS = {op.value for op in ClassifierOp}
_VALID_OPS_STR = ", ".join(op.value for op in ClassifierOp)
_VALID_TX_TYPES = {tx_type.value for tx_type in TransactionType}


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_condition_string_fields(data: dict[str, object]) -> dict[str, object]:
    for field in (
        "cond_day_month_op",
        "cond_day_week",
        "cond_amount_op",
        "cond_type",
        "cond_bank_category",
        "cond_description",
    ):
        if field in data:
            data[field] = _normalize_optional_str(data[field])  # type: ignore[arg-type]
    return data


def has_at_least_one_condition(
    *,
    cond_account_id: UUID | None,
    cond_day_month: int | None,
    cond_day_week: str | None,
    cond_amount: Decimal | None,
    cond_type: str | None,
    cond_bank_category: str | None,
    cond_description: str | None,
) -> bool:
    return not all(
        c is None
        for c in [
            cond_account_id,
            cond_day_month,
            cond_day_week,
            cond_amount,
            cond_type,
            cond_bank_category,
            cond_description,
        ]
    )


def _validate_classifier_conditions(
    *,
    cond_account_id: UUID | None,
    cond_day_month: int | None,
    cond_day_month_op: str | None,
    cond_day_month_to: int | None,
    cond_day_week: str | None,
    cond_amount: Decimal | None,
    cond_amount_op: str | None,
    cond_amount_to: Decimal | None,
    cond_type: str | None,
    cond_bank_category: str | None,
    cond_description: str | None,
    require_at_least_one: bool = True,
) -> None:
    if cond_day_month is not None:
        if not 1 <= cond_day_month <= 31:
            raise ValueError("cond_day_month must be between 1 and 31.")
        if cond_day_month_op not in _VALID_OPS:
            raise ValueError(f"cond_day_month_op must be one of: {_VALID_OPS_STR}.")
        if cond_day_month_op == ClassifierOp.BETWEEN:
            if cond_day_month_to is None:
                raise ValueError(
                    f"cond_day_month_to is required when op is '{ClassifierOp.BETWEEN}'."
                )
            if not 1 <= cond_day_month_to <= 31:
                raise ValueError("cond_day_month_to must be between 1 and 31.")
            if cond_day_month >= cond_day_month_to:
                raise ValueError("cond_day_month must be less than cond_day_month_to for range.")
    if cond_amount is not None:
        if cond_amount_op not in _VALID_OPS:
            raise ValueError(f"cond_amount_op must be one of: {_VALID_OPS_STR}.")
        if cond_amount_op == ClassifierOp.BETWEEN:
            if cond_amount_to is None:
                raise ValueError(f"cond_amount_to is required when op is '{ClassifierOp.BETWEEN}'.")
            if cond_amount >= cond_amount_to:
                raise ValueError("cond_amount must be less than cond_amount_to for range.")
    if require_at_least_one and not has_at_least_one_condition(
        cond_account_id=cond_account_id,
        cond_day_month=cond_day_month,
        cond_day_week=cond_day_week,
        cond_amount=cond_amount,
        cond_type=cond_type,
        cond_bank_category=cond_bank_category,
        cond_description=cond_description,
    ):
        raise ValueError("Необходимо указать хотя бы одно условие.")
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
    cond_day_month_to: int | None = None
    cond_day_week: str | None = None
    cond_amount: Decimal | None = None
    cond_amount_op: str | None = None
    cond_amount_to: Decimal | None = None
    cond_type: str | None = None
    cond_bank_category: str | None = None
    cond_description: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_conditions(self) -> "ClassifierRuleCreate":
        self.cond_day_month_op = _normalize_optional_str(self.cond_day_month_op)
        self.cond_day_week = _normalize_optional_str(self.cond_day_week)
        self.cond_amount_op = _normalize_optional_str(self.cond_amount_op)
        self.cond_type = _normalize_optional_str(self.cond_type)
        self.cond_bank_category = _normalize_optional_str(self.cond_bank_category)
        self.cond_description = _normalize_optional_str(self.cond_description)
        _validate_classifier_conditions(
            cond_account_id=self.cond_account_id,
            cond_day_month=self.cond_day_month,
            cond_day_month_op=self.cond_day_month_op,
            cond_day_month_to=self.cond_day_month_to,
            cond_day_week=self.cond_day_week,
            cond_amount=self.cond_amount,
            cond_amount_op=self.cond_amount_op,
            cond_amount_to=self.cond_amount_to,
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
    cond_day_month_to: int | None = None
    cond_day_week: str | None = None
    cond_amount: Decimal | None = None
    cond_amount_op: str | None = None
    cond_amount_to: Decimal | None = None
    cond_type: str | None = None
    cond_bank_category: str | None = None
    cond_description: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("name", "expense_type_id")
    @classmethod
    def required_strings_must_not_be_empty_or_null(cls, v: str | None) -> str | None:
        if v is None:
            raise ValueError("Field cannot be null.")
        if not v.strip():
            raise ValueError("Field cannot be empty.")
        return v

    @field_validator("priority", "is_active")
    @classmethod
    def required_scalars_must_not_be_null(cls, v: object) -> object:
        if v is None:
            raise ValueError("Field cannot be null.")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_conditions(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        data = _normalize_condition_string_fields(dict(data))
        condition_fields = {
            "cond_account_id",
            "cond_day_month",
            "cond_day_month_op",
            "cond_day_month_to",
            "cond_day_week",
            "cond_amount",
            "cond_amount_op",
            "cond_amount_to",
            "cond_type",
            "cond_bank_category",
            "cond_description",
        }
        if not (set(data) & condition_fields):
            return data

        _validate_classifier_conditions(
            cond_account_id=data.get("cond_account_id"),  # type: ignore[arg-type]
            cond_day_month=data.get("cond_day_month"),  # type: ignore[arg-type]
            cond_day_month_op=data.get("cond_day_month_op"),  # type: ignore[arg-type]
            cond_day_month_to=data.get("cond_day_month_to"),  # type: ignore[arg-type]
            cond_day_week=data.get("cond_day_week"),  # type: ignore[arg-type]
            cond_amount=data.get("cond_amount"),  # type: ignore[arg-type]
            cond_amount_op=data.get("cond_amount_op"),  # type: ignore[arg-type]
            cond_amount_to=data.get("cond_amount_to"),  # type: ignore[arg-type]
            cond_type=data.get("cond_type"),  # type: ignore[arg-type]
            cond_bank_category=data.get("cond_bank_category"),  # type: ignore[arg-type]
            cond_description=data.get("cond_description"),  # type: ignore[arg-type]
            require_at_least_one=False,
        )
        return data


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
    cond_day_month_to: int | None
    cond_day_week: str | None
    cond_amount: Decimal | None
    cond_amount_op: str | None
    cond_amount_to: Decimal | None
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
