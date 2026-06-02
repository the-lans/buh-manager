from pydantic import BaseModel


class ExpenseTypeCreate(BaseModel):
    id: str  # slug, e.g. "grocery"
    name: str
    receipt_required: bool = True
    description: str | None = None


class ExpenseTypeUpdate(BaseModel):
    name: str | None = None
    receipt_required: bool | None = None
    description: str | None = None


class ExpenseTypeRead(BaseModel):
    id: str
    name: str
    receipt_required: bool
    description: str | None = None

    model_config = {"from_attributes": True}
