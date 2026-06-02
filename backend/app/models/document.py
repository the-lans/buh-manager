from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.utils.dt import utcnow


class Document(SQLModel, table=True):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("file_hash", "user_id", name="uq_document_file_hash_user"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    type: str
    url: str
    name: str
    status: str
    email_source: str | None = None
    file_hash: str
    raw_parsed_data: str | None = None
    uploaded_at: datetime = Field(default_factory=utcnow, index=True)
    payload: dict | None = Field(default=None, sa_column=Column(JSON))
