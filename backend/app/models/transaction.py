from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.constants import ImportStatus, ReconciledStatus


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "occurred_at", "balance_after", name="uq_transaction_dedup"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    account_id: UUID = Field(foreign_key="accounts.id", index=True)
    occurred_at: datetime
    processed_at: datetime | None = None
    auth_code: str | None = None
    amount: Decimal = Field(decimal_places=2, max_digits=14)
    type: str
    bank_category: str | None = None
    counterparty_id: str | None = Field(default=None, foreign_key="counterparties.id")
    expense_type_id: str | None = Field(default=None, foreign_key="expense_types.id")
    description: str | None = None
    balance_after: Decimal | None = Field(default=None, decimal_places=2, max_digits=14)
    calculated_balance_after: Decimal | None = Field(default=None, decimal_places=2, max_digits=14)
    balance_mismatch: bool = Field(default=False)
    receipt_id: UUID | None = Field(default=None, foreign_key="receipts.id", unique=True)
    reconciled_status: str = Field(default=ReconciledStatus.UNMATCHED)
    import_status: str = Field(default=ImportStatus.IMPORTED)
    document_id: UUID | None = Field(default=None, foreign_key="documents.id")
