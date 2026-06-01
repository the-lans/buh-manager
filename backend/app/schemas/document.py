from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator


class DocumentRead(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    url: str
    name: str
    status: str
    email_source: str | None
    file_hash: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: UUID
    type: str
    name: str
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class LinkReceiptRequest(BaseModel):
    receipt_id: UUID


class LinkStatementRequest(BaseModel):
    account_id: UUID
    statement_start: datetime
    statement_end: datetime

    @model_validator(mode="after")
    def validate_date_range(self) -> "LinkStatementRequest":
        if self.statement_start >= self.statement_end:
            raise ValueError("statement_start must be before statement_end")
        return self


class LinkResult(BaseModel):
    document_id: UUID
    status: str
    updated_count: int
    message: str | None = None
