from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.utils.dt import normalize_to_utc


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
    amount: Decimal
    recorded_at: datetime
    source: Literal["OPENING", "CLOSING"]

    @field_validator("recorded_at", mode="after")
    @classmethod
    def normalize_recorded_at(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)
