from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Counterparty(SQLModel, table=True):
    __tablename__ = "counterparties"

    id: str = Field(primary_key=True)
    name: str
    type: str
    inn: str | None = Field(default=None, max_length=12, unique=True)
    kpp: str | None = Field(default=None, max_length=9)
    payload: dict | None = Field(default=None, sa_column=Column(JSON))
