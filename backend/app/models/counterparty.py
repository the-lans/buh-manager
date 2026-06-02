from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Counterparty(SQLModel, table=True):
    __tablename__ = "counterparties"
    __table_args__ = (UniqueConstraint("user_id", "inn", name="uq_counterparty_user_inn"),)

    id: str = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str
    type: str
    inn: str | None = Field(default=None, max_length=12)
    kpp: str | None = Field(default=None, max_length=9)
