from collections.abc import Generator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, _connection_record: object) -> None:
    # Enable FK enforcement for SQLite connections
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def drop_db_and_tables() -> None:
    SQLModel.metadata.drop_all(engine)
