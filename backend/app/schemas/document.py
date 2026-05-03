from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
