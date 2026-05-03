from pydantic import BaseModel


class ExpenseTypeCreate(BaseModel):
    id: str  # slug, e.g. "grocery"
    name: str
    receipt_required: bool = True


class ExpenseTypeUpdate(BaseModel):
    name: str | None = None
    receipt_required: bool | None = None


class ExpenseTypeRead(BaseModel):
    id: str
    name: str
    receipt_required: bool

    model_config = {"from_attributes": True}
