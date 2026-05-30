import hashlib
import json
import secrets
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.constants import ApiKeyScope
from app.db.api_keys import create_api_key
from app.models.user import User


def _make_api_key_in_db(
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


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, auth_headers: dict, test_user: User) -> None:
    resp = await client.post(
        "/api/v1/api-keys",
        json={
            "name": "My integration key",
            "scopes": [ApiKeyScope.READ_RECEIPTS, ApiKeyScope.WRITE_RECEIPTS],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My integration key"
    assert "key" in data
    assert data["key"].startswith("bm_")
    assert len(data["key_prefix"]) == 8
    assert "id" in data
    assert data["is_active"] is True
    assert set(data["scopes"]) == {ApiKeyScope.READ_RECEIPTS, ApiKeyScope.WRITE_RECEIPTS}


@pytest.mark.asyncio
async def test_created_key_not_in_list(client: AsyncClient, auth_headers: dict, test_user: User) -> None:
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Secret key", "scopes": [ApiKeyScope.READ_DOCUMENTS]},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    created_key_value = create_resp.json()["key"]

    list_resp = await client.get("/api/v1/api-keys", headers=auth_headers)
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert len(keys) == 1
    assert "key" not in keys[0]
    assert keys[0]["name"] == "Secret key"
    # confirm plaintext is not in response
    assert created_key_value not in json.dumps(keys)


@pytest.mark.asyncio
async def test_list_api_keys_empty(client: AsyncClient, auth_headers: dict) -> None:
    resp = await client.get("/api/v1/api-keys", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_user_can_create_multiple_keys(client: AsyncClient, auth_headers: dict) -> None:
    for i in range(3):
        resp = await client.post(
            "/api/v1/api-keys",
            json={"name": f"Key {i}", "scopes": [ApiKeyScope.READ_TRANSACTIONS]},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    list_resp = await client.get("/api/v1/api-keys", headers=auth_headers)
    assert len(list_resp.json()) == 3


@pytest.mark.asyncio
async def test_update_api_key(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Old name", "scopes": [ApiKeyScope.READ_DOCUMENTS]},
        headers=auth_headers,
    )
    key_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/api-keys/{key_id}",
        json={"name": "New name", "scopes": [ApiKeyScope.READ_RECEIPTS, ApiKeyScope.WRITE_RECEIPTS]},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "New name"
    assert set(data["scopes"]) == {ApiKeyScope.READ_RECEIPTS, ApiKeyScope.WRITE_RECEIPTS}


@pytest.mark.asyncio
async def test_deactivate_api_key(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Active key", "scopes": [ApiKeyScope.READ_DOCUMENTS]},
        headers=auth_headers,
    )
    key_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/api-keys/{key_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_api_key(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "To delete", "scopes": [ApiKeyScope.READ_DOCUMENTS]},
        headers=auth_headers,
    )
    key_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/v1/api-keys", headers=auth_headers)
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_key_returns_404(client: AsyncClient, auth_headers: dict) -> None:
    from uuid import uuid4
    resp = await client.delete(f"/api/v1/api-keys/{uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_key_management_requires_jwt(
    client: AsyncClient, session: Session, test_user: User
) -> None:
    plaintext = _make_api_key_in_db(
        session, test_user.id, [ApiKeyScope.READ_DOCUMENTS]
    )
    api_key_headers = {"Authorization": f"Bearer {plaintext}"}

    resp = await client.get("/api/v1/api-keys", headers=api_key_headers)
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "sub-key", "scopes": [ApiKeyScope.READ_DOCUMENTS]},
        headers=api_key_headers,
    )
    assert resp.status_code == 403
