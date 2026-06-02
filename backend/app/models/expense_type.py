from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ExpenseType(SQLModel, table=True):
    __tablename__ = "expense_types"
    __table_args__ = (UniqueConstraint("user_id", "id", name="uq_expense_type_user_id_id"),)

    id: str = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str
    receipt_required: bool = Field(default=True)
