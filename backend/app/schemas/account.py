from uuid import UUID

from pydantic import BaseModel


class AccountCreate(BaseModel):
    bank: str
    account_number: str
    currency: str = "RUB"


class AccountUpdate(BaseModel):
    bank: str | None = None
    account_number: str | None = None
    currency: str | None = None
    is_active: bool | None = None


class AccountRead(BaseModel):
    id: UUID
    user_id: UUID
    bank: str
    account_number: str
    currency: str
    is_active: bool
    has_balances: bool = False

    model_config = {"from_attributes": True}


class AccountBalanceInit(BaseModel):
    amount: float
    recorded_at: str  # ISO datetime string; parsed in router
    source: str  # "OPENING" or "CLOSING"
