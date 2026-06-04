from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Receipt(SQLModel, table=True):
    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_receipt_document_id"),
        UniqueConstraint("user_id", "fn", "fd", "fpd", name="uq_receipt_user_fiscal"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    document_id: UUID | None = Field(default=None, foreign_key="documents.id", index=True)
    paid_at: datetime = Field(index=True)
    total_amount: Decimal = Field(decimal_places=2, max_digits=14)
    counterparty_id: str | None = Field(default=None, foreign_key="counterparties.id")
    fn: str | None = None
    fd: str | None = None
    fpd: str | None = None
