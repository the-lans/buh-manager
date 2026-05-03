from sqlmodel import Field, SQLModel


class Counterparty(SQLModel, table=True):
    __tablename__ = "counterparties"

    id: str = Field(primary_key=True)
    name: str
    type: str
