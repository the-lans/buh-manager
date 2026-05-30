from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str
    key_prefix: str = Field(max_length=8)
    key_hash: str = Field(index=True, unique=True)
    scopes: str  # JSON array of ApiKeyScope values
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
