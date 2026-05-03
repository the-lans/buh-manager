from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ReconciliationReportRecord(SQLModel, table=True):
    __tablename__ = "reconciliation_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_json: str
