from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class AppConstant(SQLModel, table=True):
    __tablename__ = "app_constants"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_app_constant_user_key"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    key: str
    value: str
