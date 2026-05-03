from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    entity_type: str
    entity_id: UUID
    action: str
    changed_by: str
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    diff: str | None = None  # JSON: {"before": {...}, "after": {...}}
