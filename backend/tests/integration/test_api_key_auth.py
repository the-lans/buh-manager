import hashlib
import secrets
from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.constants import ApiKeyScope
from app.models.api_key import ApiKey
from app.models.user import User
from app.utils.dt import utcnow


@pytest.mark.asyncio
async def test_api_key_with_correct_scope_is_accepted(
    client: AsyncClient, test_user: User, make_api_key_in_db: Callable[..., str]
) -> None:
    key = make_api_key_in_db(test_user.id, [ApiKeyScope.READ_RECEIPTS])
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_with_wrong_scope_returns_403(
    client: AsyncClient, test_user: User, make_api_key_in_db: Callable[..., str]
) -> None:
    key = make_api_key_in_db(test_user.id, [ApiKeyScope.READ_DOCUMENTS])
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 403
    assert "scope" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_write_scope_required_for_mutation(
    client: AsyncClient, test_user: User, make_api_key_in_db: Callable[..., str]
) -> None:
    key = make_api_key_in_db(test_user.id, [ApiKeyScope.READ_RECEIPTS])
    resp = await client.post(
        "/api/v1/receipts",
        json={"paid_at": "2024-01-01T00:00:00", "total_amount": "100.00"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_inactive_api_key_returns_401(
    client: AsyncClient, test_user: User, make_api_key_in_db: Callable[..., str]
) -> None:
    key = make_api_key_in_db(test_user.id, [ApiKeyScope.READ_RECEIPTS], is_active=False)
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_api_key_returns_401(
    client: AsyncClient, test_user: User, make_api_key_in_db: Callable[..., str]
) -> None:
    past = utcnow() - timedelta(days=1)
    key = make_api_key_in_db(test_user.id, [ApiKeyScope.READ_RECEIPTS], expires_at=past)
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_nonexistent_api_key_returns_401(client: AsyncClient) -> None:
    fake_key = f"bm_{secrets.token_urlsafe(32)}"
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {fake_key}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/api/v1/receipts",
    "/api/v1/transactions",
])
async def test_jwt_bypasses_scope_check(
    client: AsyncClient, auth_headers: dict[str, str], path: str
) -> None:
    resp = await client.get(path, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_last_used_updated(
    client: AsyncClient,
    session: Session,
    test_user: User,
    make_api_key_in_db: Callable[..., str],
) -> None:
    key = make_api_key_in_db(test_user.id, [ApiKeyScope.WRITE_COUNTERPARTIES])
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    api_key_obj = session.exec(select(ApiKey).where(ApiKey.key_hash == key_hash)).first()
    assert api_key_obj is not None
    assert api_key_obj.last_used_at is None

    # Use a write endpoint so the request session commits, persisting last_used_at.
    await client.post(
        "/api/v1/counterparties",
        json={"name": "Test counterparty"},
        headers={"Authorization": f"Bearer {key}"},
    )

    session.refresh(api_key_obj)
    assert api_key_obj.last_used_at is not None


@pytest.mark.asyncio
async def test_api_key_isolates_data_per_user(
    client: AsyncClient,
    session: Session,
    test_user: User,
    make_api_key_in_db: Callable[..., str],
) -> None:
    other_user = User(
        id=uuid4(),
        email="other@example.com",
        full_name="Other User",
        is_active=True,
        created_at=utcnow(),
    )
    session.add(other_user)
    session.commit()

    key_a = make_api_key_in_db(test_user.id, [ApiKeyScope.READ_RECEIPTS])
    key_b = make_api_key_in_db(other_user.id, [ApiKeyScope.READ_RECEIPTS])

    resp_a = await client.get("/api/v1/receipts", headers={"Authorization": f"Bearer {key_a}"})
    resp_b = await client.get("/api/v1/receipts", headers={"Authorization": f"Bearer {key_b}"})

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json() == []
    assert resp_b.json() == []
