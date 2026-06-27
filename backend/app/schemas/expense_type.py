from pydantic import BaseModel, field_serializer

from app.utils.ids import unscope_user_id


class ExpenseTypeCreate(BaseModel):
    id: str  # slug, e.g. "grocery"
    name: str
    description: str | None = None
    receipt_required: bool = True
    exclude_from_expenses: bool = False


class ExpenseTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    receipt_required: bool | None = None
    exclude_from_expenses: bool | None = None


class ExpenseTypeRead(BaseModel):
    id: str
    name: str
    description: str | None
    receipt_required: bool
    exclude_from_expenses: bool

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, value: str) -> str:
        return unscope_user_id(value) or value
