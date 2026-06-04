from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from app.constants import DocumentStatus, DocumentType
from app.utils.dt import normalize_to_utc


class DocumentRead(BaseModel):
    id: UUID
    user_id: UUID
    type: DocumentType
    url: str
    name: str
    status: DocumentStatus
    email_source: str | None
    file_hash: str
    uploaded_at: datetime
    payload: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    payload: dict[str, Any] | None = None


class DocumentListItem(BaseModel):
    id: UUID
    type: DocumentType
    name: str
    status: DocumentStatus
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class LinkReceiptRequest(BaseModel):
    receipt_id: UUID


class LinkStatementRequest(BaseModel):
    account_id: UUID
    statement_start: datetime
    statement_end: datetime

    @field_validator("statement_start", "statement_end", mode="after")
    @classmethod
    def normalize_period(cls, v: datetime) -> datetime:
        return normalize_to_utc(v)

    @model_validator(mode="after")
    def validate_date_range(self) -> "LinkStatementRequest":
        if self.statement_start >= self.statement_end:
            raise ValueError("statement_start must be before statement_end")
        return self


class LinkResult(BaseModel):
    document_id: UUID
    status: DocumentStatus
    updated_count: int
    message: str | None = None
