from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ExchangeRateCreate(BaseModel):
    base_currency: str
    quote_currency: str
    rate: Decimal
    recorded_at: datetime | None = None


class ExchangeRateRead(BaseModel):
    id: UUID
    base_currency: str
    quote_currency: str
    rate: Decimal
    recorded_at: datetime

    model_config = {"from_attributes": True}
