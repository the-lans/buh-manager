from collections.abc import AsyncGenerator, Callable, Generator
from datetime import datetime, timedelta
from sqlite3 import Connection as SQLiteConnection
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings
from app.database import get_session
from app.db.api_keys import create_api_key
from app.dependencies.auth import generate_api_key
from app.main import app
from app.models.account import Account
from app.models.expense_type import ExpenseType
from app.models.user import User
from app.utils.dt import utcnow
from app.utils.ids import scope_user_id
from storage import get_storage_provider
from storage.base import StorageProvider

# ── In-memory SQLite engine ──────────────────────────────────────────────────


@pytest.fixture(scope="function")
def engine() -> Generator[Engine, None, None]:
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def set_pragma(dbapi_conn: SQLiteConnection, _: object) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture(scope="function")
def session(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as s:
        yield s


# ── Fixture users / accounts ─────────────────────────────────────────────────


@pytest.fixture()
def test_user(session: Session) -> User:
    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        created_at=utcnow(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def second_test_user(session: Session) -> User:
    user = User(
        id=uuid4(),
        email="second@example.com",
        full_name="Second User",
        is_active=True,
        created_at=utcnow(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def test_account(session: Session, test_user: User) -> Account:
    account = Account(
        id=uuid4(),
        user_id=test_user.id,
        bank="TestBank",
        account_number="40817810000000000001",
        currency="RUB",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@pytest.fixture()
def test_expense_type_id(session: Session, test_user: User) -> str:
    """Creates a default expense type for test_user; returns the public ID."""
    public_id = "test-et"
    et = ExpenseType(
        id=scope_user_id(user_id=test_user.id, public_id=public_id),
        user_id=test_user.id,
        name="Тест расхода",
        receipt_required=True,
    )
    session.add(et)
    session.commit()
    return public_id


@pytest.fixture()
def test_expense_type_scoped_id(test_user: User, test_expense_type_id: str) -> str:
    """Returns the scoped (internal DB) ID of the test expense type. Use this for direct DB inserts."""
    return scope_user_id(user_id=test_user.id, public_id=test_expense_type_id)


@pytest.fixture()
def second_test_expense_type_id(session: Session, second_test_user: User) -> str:
    """Creates a default expense type for second_test_user; returns the public ID."""
    public_id = "test-et"
    et = ExpenseType(
        id=scope_user_id(user_id=second_test_user.id, public_id=public_id),
        user_id=second_test_user.id,
        name="Тест расхода 2",
        receipt_required=True,
    )
    session.add(et)
    session.commit()
    return public_id


@pytest.fixture()
def second_test_account(session: Session, second_test_user: User) -> Account:
    account = Account(
        id=uuid4(),
        user_id=second_test_user.id,
        bank="SecondTestBank",
        account_number="40817810000000000002",
        currency="RUB",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


# ── JWT helper ───────────────────────────────────────────────────────────────


def make_jwt(user_id: str) -> str:
    expire = utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    return cast(
        "str",
        jwt.encode(
            {"sub": user_id, "exp": expire},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        ),
    )


# ── Fake storage provider ────────────────────────────────────────────────────


class FakeStorageProvider:
    async def upload_file(self, *, file: UploadFile, file_id: str) -> str:  # noqa: ARG002
        return f"/media/fake/{file_id}"

    async def delete_file(self, *, doc_url: str) -> None:  # noqa: ARG002
        return None

    def get_download_url(
        self,
        *,
        doc_url: str,
        filename: str,  # noqa: ARG002
        inline: bool = False,  # noqa: ARG002
        expires_in: int = 3600,  # noqa: ARG002
    ) -> str:
        return doc_url


# ── HTTP client for integration tests ────────────────────────────────────────


@pytest.fixture()
async def client(engine: Engine) -> AsyncGenerator[AsyncClient, None]:
    def override_session() -> Generator[Session, None, None]:
        with Session(engine) as s:
            yield s

    def override_storage() -> StorageProvider:
        return FakeStorageProvider()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_storage_provider] = override_storage

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(test_user: User) -> dict[str, str]:
    token = make_jwt(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_auth_headers(second_test_user: User) -> dict[str, str]:
    token = make_jwt(str(second_test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_api_key_in_db(session: Session) -> Callable[..., str]:
    def _inner(
        user_id: UUID,
        scopes: list[str],
        *,
        is_active: bool = True,
        expires_at: datetime | None = None,
    ) -> str:
        plaintext, key_hash, key_prefix = generate_api_key()
        api_key_obj = create_api_key(
            session=session,
            user_id=user_id,
            name="test key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            expires_at=expires_at,
        )
        api_key_obj.is_active = is_active
        session.commit()
        return plaintext

    return _inner
