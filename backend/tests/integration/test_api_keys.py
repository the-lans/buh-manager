import json
from collections.abc import Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.constants import ApiKeyScope
from app.models.user import User


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, auth_headers: dict[str, str]) -> None:
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
    assert data["is_active"] is True
    assert set(data["scopes"]) == {ApiKeyScope.READ_RECEIPTS, ApiKeyScope.WRITE_RECEIPTS}
    assert "id" in data

    # Key format: "bm_" prefix + random, ≥ 36 chars, key_prefix is the first 8 random chars
    key: str = data["key"]
    assert key.startswith("bm_")
    assert len(key) >= 36
    assert len(data["key_prefix"]) == 8
    assert key[3:11] == data["key_prefix"]


@pytest.mark.asyncio
async def test_created_key_not_in_list(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
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
    assert created_key_value not in json.dumps(keys)


@pytest.mark.asyncio
async def test_list_api_keys_empty(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get("/api/v1/api-keys", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_user_can_create_multiple_keys(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
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
async def test_update_api_key(client: AsyncClient, auth_headers: dict[str, str]) -> None:
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
async def test_deactivate_api_key(client: AsyncClient, auth_headers: dict[str, str]) -> None:
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
async def test_delete_api_key(client: AsyncClient, auth_headers: dict[str, str]) -> None:
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
async def test_delete_nonexistent_key_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.delete(f"/api/v1/api-keys/{uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ── Validation tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    {"name": "", "scopes": ["read:receipts"]},
    {"name": "   ", "scopes": ["read:receipts"]},
    {"name": "valid", "scopes": []},
    {"scopes": ["read:receipts"]},  # missing required name
    {"name": "valid", "scopes": ["read:receipts"], "expires_at": "2020-01-01T00:00:00"},
])
async def test_create_api_key_invalid_input(
    body: dict,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post("/api/v1/api-keys", json=body, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("patch_body", [
    {"name": ""},
    {"name": "   "},
    {"scopes": []},
])
async def test_update_api_key_invalid_input(
    patch_body: dict,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Valid key", "scopes": [ApiKeyScope.READ_RECEIPTS]},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    key_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/api-keys/{key_id}",
        json=patch_body,
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── Access control tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path_template,extra_kwargs",
    [
        ("get", "/api/v1/api-keys", {}),
        (
            "post",
            "/api/v1/api-keys",
            {"json": {"name": "sub-key", "scopes": [ApiKeyScope.READ_DOCUMENTS]}},
        ),
    ],
)
async def test_api_key_management_requires_jwt(
    method: str,
    path_template: str,
    extra_kwargs: dict,
    client: AsyncClient,
    test_user: User,
    make_api_key_in_db: Callable[..., str],
) -> None:
    plaintext = make_api_key_in_db(test_user.id, [ApiKeyScope.READ_DOCUMENTS])
    api_key_headers = {"Authorization": f"Bearer {plaintext}"}
    resp = await getattr(client, method)(path_template, headers=api_key_headers, **extra_kwargs)
    assert resp.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,extra_kwargs",
    [
        ("patch", {"json": {"name": "Hacked"}}),
        ("delete", {}),
    ],
)
async def test_user_cannot_manage_another_users_key(
    method: str,
    extra_kwargs: dict,
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Owner's key", "scopes": [ApiKeyScope.READ_RECEIPTS]},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    key_id = create_resp.json()["id"]

    resp = await getattr(client, method)(
        f"/api/v1/api-keys/{key_id}",
        headers=second_auth_headers,
        **extra_kwargs,
    )
    assert resp.status_code == 404


# ── End-to-end lifecycle test ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_key_full_lifecycle(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Simulates a user creating, using, deactivating, reactivating, and deleting a key."""
    # 1. Create key via JWT auth
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Lifecycle key", "scopes": [ApiKeyScope.READ_RECEIPTS]},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    key_id: str = create_resp.json()["id"]
    key: str = create_resp.json()["key"]
    api_headers = {"Authorization": f"Bearer {key}"}

    # 2. Key works for the granted scope
    resp = await client.get("/api/v1/receipts", headers=api_headers)
    assert resp.status_code == 200

    # 3. Key does NOT work for a scope it was not granted
    resp = await client.get("/api/v1/transactions", headers=api_headers)
    assert resp.status_code == 403

    # 4. Deactivate key
    resp = await client.patch(
        f"/api/v1/api-keys/{key_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 5. Deactivated key returns 401
    resp = await client.get("/api/v1/receipts", headers=api_headers)
    assert resp.status_code == 401

    # 6. Reactivate key
    resp = await client.patch(
        f"/api/v1/api-keys/{key_id}",
        json={"is_active": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    # 7. Key works again after reactivation
    resp = await client.get("/api/v1/receipts", headers=api_headers)
    assert resp.status_code == 200

    # 8. Delete key
    resp = await client.delete(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
    assert resp.status_code == 204

    # 9. Key returns 401 after deletion
    resp = await client.get("/api/v1/receipts", headers=api_headers)
    assert resp.status_code == 401

    # 10. Key no longer appears in list
    list_resp = await client.get("/api/v1/api-keys", headers=auth_headers)
    assert list_resp.json() == []
