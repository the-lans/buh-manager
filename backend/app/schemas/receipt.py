import json
import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_serializer, field_validator

from app.utils.dt import normalize_to_utc
from app.utils.ids import unscope_user_id

_INN_RE = re.compile(r"^\d{10}(\d{2})?$")


class ReceiptItemCreate(BaseModel):
    code: str | None = None
    name: str
    unit: str | None = None
    quantity: Decimal
    price: Decimal
    amount: Decimal
    tags: list[str] | None = None


class ReceiptCreate(BaseModel):
    document_id: UUID | None = None
    counterparty_id: str | None = None
    counterparty_name: str | None = None
    counterparty_inn: str | None = None
    paid_at: datetime
    total_amount: Decimal
    fn: str | None = None
    fd: str | None = None
    fpd: str | None = None
    items: list[ReceiptItemCreate] = []

    @field_validator("counterparty_inn")
    @classmethod
    def validate_counterparty_inn(cls, v: str | None) -> str | None:
        if v is not None and not _INN_RE.match(v):
            raise ValueError("ИНН должен содержать 10 или 12 цифр")
        return v

    @field_validator("paid_at", mode="after")
    @classmethod
    def normalize_paid_at(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)


class ReceiptUpdate(BaseModel):
    document_id: UUID | None = None
    counterparty_id: str | None = None
    paid_at: datetime | None = None
    total_amount: Decimal | None = None
    fn: str | None = None
    fd: str | None = None
    fpd: str | None = None

    @field_validator("paid_at", mode="after")
    @classmethod
    def normalize_paid_at(cls, v: datetime | None) -> datetime | None:
        return normalize_to_utc(v) if v is not None else None


class ReceiptItemRead(BaseModel):
    id: UUID
    code: str | None
    name: str
    unit: str | None
    quantity: Decimal
    price: Decimal
    amount: Decimal
    tags: list[str] | None

    model_config = {"from_attributes": True}

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: str | list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
        return None


class ReceiptRead(BaseModel):
    id: UUID
    document_id: UUID | None
    paid_at: datetime
    total_amount: Decimal
    counterparty_id: str | None
    fn: str | None
    fd: str | None
    fpd: str | None
    items: list[ReceiptItemRead] = []

    model_config = {"from_attributes": True}

    @field_serializer("counterparty_id")
    def serialize_counterparty_id(self, value: str | None) -> str | None:
        return unscope_user_id(value)


class ReceiptListItem(BaseModel):
    id: UUID
    paid_at: datetime
    total_amount: Decimal
    counterparty_id: str | None
    document_id: UUID | None
    transaction_id: UUID | None = None

    model_config = {"from_attributes": True}

    @field_serializer("counterparty_id")
    def serialize_counterparty_id(self, value: str | None) -> str | None:
        return unscope_user_id(value)
