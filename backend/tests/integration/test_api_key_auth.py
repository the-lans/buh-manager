import hashlib
import json
import secrets
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.constants import ApiKeyScope
from app.db.api_keys import create_api_key
from app.models.api_key import ApiKey
from app.models.user import User


def _make_api_key(
    session: Session,
    user_id,
    scopes: list[str],
    *,
    is_active: bool = True,
    expires_at: datetime | None = None,
) -> str:
    plaintext = f"bm_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    key_prefix = plaintext[3:11]
    create_api_key(
        session=session,
        user_id=user_id,
        name="test key",
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes,
        expires_at=expires_at,
    )
    api_key_obj = session.exec(select(ApiKey).where(ApiKey.key_hash == key_hash)).first()
    if api_key_obj is not None:
        api_key_obj.is_active = is_active
        session.add(api_key_obj)
    session.commit()
    return plaintext


@pytest.mark.asyncio
async def test_api_key_with_correct_scope_is_accepted(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    key = _make_api_key(session, test_user.id, [ApiKeyScope.READ_RECEIPTS])
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_with_wrong_scope_returns_403(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    key = _make_api_key(session, test_user.id, [ApiKeyScope.READ_DOCUMENTS])
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 403
    assert "scope" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_write_scope_required_for_mutation(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    key = _make_api_key(session, test_user.id, [ApiKeyScope.READ_RECEIPTS])
    resp = await client.post(
        "/api/v1/receipts",
        json={"paid_at": "2024-01-01T00:00:00", "total_amount": "100.00"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_inactive_api_key_returns_401(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    key = _make_api_key(session, test_user.id, [ApiKeyScope.READ_RECEIPTS], is_active=False)
    resp = await client.get(
        "/api/v1/receipts",
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_api_key_returns_401(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    past = datetime.utcnow() - timedelta(days=1)
    key = _make_api_key(session, test_user.id, [ApiKeyScope.READ_RECEIPTS], expires_at=past)
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
async def test_jwt_bypasses_scope_check(
    client: AsyncClient, auth_headers: dict
) -> None:
    resp = await client.get("/api/v1/receipts", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get("/api/v1/transactions", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_last_used_updated(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    key = _make_api_key(session, test_user.id, [ApiKeyScope.READ_RECEIPTS])
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    api_key_obj = session.exec(select(ApiKey).where(ApiKey.key_hash == key_hash)).first()
    assert api_key_obj is not None
    assert api_key_obj.last_used_at is None

    await client.get("/api/v1/receipts", headers={"Authorization": f"Bearer {key}"})

    session.refresh(api_key_obj)
    assert api_key_obj.last_used_at is not None


@pytest.mark.asyncio
async def test_api_key_isolates_data_per_user(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    from uuid import uuid4
    from app.models.user import User as UserModel

    other_user = UserModel(
        id=uuid4(),
        email="other@example.com",
        full_name="Other User",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    session.add(other_user)
    session.commit()

    key_a = _make_api_key(session, test_user.id, [ApiKeyScope.READ_RECEIPTS])
    key_b = _make_api_key(session, other_user.id, [ApiKeyScope.READ_RECEIPTS])

    resp_a = await client.get("/api/v1/receipts", headers={"Authorization": f"Bearer {key_a}"})
    resp_b = await client.get("/api/v1/receipts", headers={"Authorization": f"Bearer {key_b}"})

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json() == []
    assert resp_b.json() == []
