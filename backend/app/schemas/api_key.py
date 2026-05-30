from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.constants import ApiKeyScope


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[ApiKeyScope]
    expires_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be empty.")
        return v

    @field_validator("scopes")
    @classmethod
    def scopes_not_empty(cls, v: list[ApiKeyScope]) -> list[ApiKeyScope]:
        if not v:
            raise ValueError("At least one scope is required.")
        return v


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    scopes: list[ApiKeyScope] | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Name must not be empty.")
        return v

    @field_validator("scopes")
    @classmethod
    def scopes_not_empty(cls, v: list[ApiKeyScope] | None) -> list[ApiKeyScope] | None:
        if v is not None and not v:
            raise ValueError("At least one scope is required.")
        return v


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
