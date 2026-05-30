from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.utils.dt import normalize_to_utc


class ExchangeRateCreate(BaseModel):
    base_currency: str
    quote_currency: str
    rate: Decimal
    recorded_at: datetime | None = None

    @field_validator("recorded_at", mode="after")
    @classmethod
    def normalize_recorded_at(cls, v: datetime | None) -> datetime | None:
        return normalize_to_utc(v) if v is not None else None


class ExchangeRateRead(BaseModel):
    id: UUID
    base_currency: str
    quote_currency: str
    rate: Decimal
    recorded_at: datetime

    model_config = {"from_attributes": True}
