from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    type: str
    url: str
    name: str
    status: str
    email_source: str | None = None
    file_hash: str = Field(unique=True)
    raw_parsed_data: str | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
