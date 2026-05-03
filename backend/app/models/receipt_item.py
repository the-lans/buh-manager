from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ReceiptItem(SQLModel, table=True):
    __tablename__ = "receipt_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    receipt_id: UUID = Field(foreign_key="receipts.id", index=True)
    code: str | None = None
    name: str
    unit: str | None = None
    quantity: Decimal = Field(decimal_places=4, max_digits=14)
    price: Decimal = Field(decimal_places=2, max_digits=14)
    amount: Decimal = Field(decimal_places=2, max_digits=14)
    tags: str | None = None  # JSON array stored as text
