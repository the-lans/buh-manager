from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ClassifierRule(SQLModel, table=True):
    __tablename__ = "classifier_rules"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str
    expense_type_id: str = Field(foreign_key="expense_types.id")
    priority: int
    is_active: bool = Field(default=True)
    representation: str = Field(default="")

    # Conditions (NULL = condition not used)
    cond_account_id: UUID | None = Field(default=None)
    cond_day_month: int | None = Field(default=None)
    cond_day_month_op: str | None = Field(default=None)
    cond_day_month_to: int | None = Field(default=None)
    cond_day_week: str | None = Field(default=None)  # JSON array: [0,1,4] Mon=0..Sun=6
    cond_amount: Decimal | None = Field(default=None, decimal_places=2, max_digits=14)
    cond_amount_op: str | None = Field(default=None)  # "eq","lt","gt","lte","gte","between"
    cond_amount_to: Decimal | None = Field(default=None, decimal_places=2, max_digits=14)
    cond_type: str | None = Field(default=None)
    cond_bank_category: str | None = Field(default=None)
    cond_description: str | None = Field(default=None)
