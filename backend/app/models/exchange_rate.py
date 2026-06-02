from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.utils.dt import utcnow


class ExchangeRate(SQLModel, table=True):
    __tablename__ = "exchange_rates"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    base_currency: str
    quote_currency: str
    rate: Decimal = Field(decimal_places=6, max_digits=18)
    recorded_at: datetime = Field(default_factory=utcnow)
