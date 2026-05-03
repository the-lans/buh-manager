from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Receipt(SQLModel, table=True):
    __tablename__ = "receipts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    document_id: UUID | None = Field(default=None, foreign_key="documents.id", index=True)
    paid_at: datetime
    total_amount: Decimal = Field(decimal_places=2, max_digits=14)
    counterparty_id: str | None = Field(default=None, foreign_key="counterparties.id")
    fn: str | None = None
    fd: str | None = None
    fpd: str | None = None
