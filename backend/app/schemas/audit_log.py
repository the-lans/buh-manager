from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    changed_by: str
    changed_at: datetime
    diff: str | None

    model_config = {"from_attributes": True}
