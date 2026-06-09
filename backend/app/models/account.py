from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    bank: str
    account_number: str
    currency: str = Field(default="RUB")
    is_active: bool = Field(default=True)
    zero_balance: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(14, 2), nullable=False, server_default="0"),
    )
