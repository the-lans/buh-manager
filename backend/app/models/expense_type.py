from sqlmodel import Field, SQLModel


class ExpenseType(SQLModel, table=True):
    __tablename__ = "expense_types"

    id: str = Field(primary_key=True)
    name: str
    receipt_required: bool = Field(default=True)
