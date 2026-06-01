from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class BalanceRead(BaseModel):
    id: UUID
    account_id: UUID
    amount: Decimal
    recorded_at: datetime
    source: str
    document_id: UUID | None

    model_config = {"from_attributes": True}
