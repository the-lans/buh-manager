from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    bank: str
    account_number: str
    currency: str = Field(default="RUB")
    is_active: bool = Field(default=True)
