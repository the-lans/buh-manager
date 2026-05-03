from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


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
    counterparty_name: str | None = None
    paid_at: datetime
    total_amount: Decimal
    fn: str | None = None
    fd: str | None = None
    fpd: str | None = None
    items: list[ReceiptItemCreate] = []


class ReceiptUpdate(BaseModel):
    counterparty_name: str | None = None
    paid_at: datetime | None = None
    total_amount: Decimal | None = None
    fn: str | None = None
    fd: str | None = None
    fpd: str | None = None


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


class ReceiptListItem(BaseModel):
    id: UUID
    paid_at: datetime
    total_amount: Decimal
    counterparty_id: str | None
    document_id: UUID | None

    model_config = {"from_attributes": True}
