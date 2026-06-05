from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, field_serializer, field_validator

from app.utils.dt import normalize_to_utc
from app.utils.ids import unscope_user_id


class TransactionCreate(BaseModel):
    account_id: UUID
    occurred_at: datetime
    processed_at: datetime | None = None
    auth_code: str | None = None
    amount: Decimal
    type: str
    bank_category: str | None = None
    expense_type_id: str
    description: str | None = None
    balance_after: Decimal | None = None
    apply_rules: bool = False

    model_config = {"extra": "forbid"}

    @field_validator("occurred_at", mode="after")
    @classmethod
    def normalize_occurred_at(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)

    @field_validator("processed_at", mode="after")
    @classmethod
    def normalize_processed_at(cls, v: datetime | None) -> datetime | None:
        return normalize_to_utc(v) if v is not None else None


class TransactionUpdate(BaseModel):
    occurred_at: datetime | None = None
    amount: Decimal | None = None
    type: str | None = None
    bank_category: str | None = None
    expense_type_id: str | None = None
    description: str | None = None
    apply_rules: bool = False

    model_config = {"extra": "forbid"}

    @field_validator("expense_type_id")
    @classmethod
    def expense_type_id_must_not_be_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("expense_type_id must not be empty.")
        return v

    @field_validator("occurred_at", mode="after")
    @classmethod
    def normalize_occurred_at(cls, v: datetime | None) -> datetime | None:
        return normalize_to_utc(v) if v is not None else None


class TransactionRead(BaseModel):
    id: UUID
    account_id: UUID
    occurred_at: datetime
    processed_at: datetime | None
    auth_code: str | None
    amount: Decimal
    type: str
    bank_category: str | None
    expense_type_id: str
    description: str | None
    balance_after: Decimal | None
    calculated_balance_after: Decimal | None
    balance_mismatch: bool
    receipt_id: UUID | None
    reconciled_status: str
    import_status: str
    document_id: UUID | None

    model_config = {"from_attributes": True}

    @field_serializer("expense_type_id")
    def serialize_reference_ids(self, value: str | None) -> str | None:
        return unscope_user_id(value)


class TransactionListItem(BaseModel):
    id: UUID
    account_id: UUID
    occurred_at: datetime
    amount: Decimal
    type: str
    bank_category: str | None
    expense_type_id: str
    description: str | None
    reconciled_status: str
    import_status: str
    balance_mismatch: bool
    receipt_id: UUID | None
    document_id: UUID | None

    model_config = {"from_attributes": True}

    @field_serializer("expense_type_id")
    def serialize_reference_ids(self, value: str | None) -> str | None:
        return unscope_user_id(value)


class TransactionFilters:
    def __init__(
        self,
        account_id: UUID | None = Query(default=None),
        start_date: datetime | None = Query(default=None),
        end_date: datetime | None = Query(default=None),
        type: str | None = Query(default=None),
        reconciled_status: str | None = Query(default=None),
        import_status: str | None = Query(default=None),
    ) -> None:
        self.account_id = account_id
        self.start_date = start_date
        self.end_date = end_date
        self.type = type
        self.reconciled_status = reconciled_status
        self.import_status = import_status
