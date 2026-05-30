from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.constants import ApiKeyScope


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[ApiKeyScope]
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def scopes_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one scope is required.")
        return v


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    scopes: list[ApiKeyScope] | None = None
    is_active: bool | None = None


class ApiKeyRead(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyRead):
    key: str
