"""T79: Conflict resolution parametrized tests."""
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.account import Account


async def _make_tx(client: AsyncClient, headers: dict, account_id: str) -> str:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "occurred_at": "2024-03-01T10:00:00",
            "amount": -50.0,
            "type": "EXPENSE",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.parametrize(
    "action, expected_action_echo",
    [
        ("KEEP_OLD", "KEEP_OLD"),
        ("UPDATE_FROM_NEW", "UPDATE_FROM_NEW"),
    ],
)
@pytest.mark.asyncio
async def test_resolve_conflict_actions(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    action: str,
    expected_action_echo: str,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id))
    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": action},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["action"] == expected_action_echo


@pytest.mark.asyncio
async def test_resolve_conflict_nonexistent(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": str(uuid4()), "action": "KEEP_OLD"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
