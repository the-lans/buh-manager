from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Balance(SQLModel, table=True):
    __tablename__ = "balances"
    __table_args__ = (
        UniqueConstraint("account_id", "recorded_at", "source", name="uq_balance_snapshot"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    account_id: UUID = Field(foreign_key="accounts.id", index=True)
    amount: Decimal = Field(decimal_places=2, max_digits=14)
    recorded_at: datetime
    source: str
    document_id: UUID | None = Field(default=None, foreign_key="documents.id")
