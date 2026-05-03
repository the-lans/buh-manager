from uuid import UUID

from pydantic import BaseModel


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}
