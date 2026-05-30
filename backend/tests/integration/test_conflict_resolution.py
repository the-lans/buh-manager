"""T79: Conflict resolution parametrized tests."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.constants import ImportStatus
from app.models.account import Account
from app.models.transaction import Transaction


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


@pytest.mark.asyncio
async def test_resolve_conflict_keep_old_preserves_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_account: Account,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id))
    tx = session.get(Transaction, UUID(tx_id))
    assert tx is not None
    tx.import_status = ImportStatus.CONFLICT
    session.add(tx)
    session.commit()

    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": "KEEP_OLD"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["action"] == "KEEP_OLD"

    session.refresh(tx)
    assert tx.amount == Decimal("-50.00")
    assert tx.import_status == ImportStatus.IMPORTED


@pytest.mark.asyncio
async def test_resolve_conflict_update_from_new_changes_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_account: Account,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id))
    tx = session.get(Transaction, UUID(tx_id))
    assert tx is not None
    tx.import_status = ImportStatus.CONFLICT
    session.add(tx)
    session.commit()

    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": "UPDATE_FROM_NEW", "incoming_amount": "-75.25"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["action"] == "UPDATE_FROM_NEW"

    session.refresh(tx)
    assert tx.amount == Decimal("-75.25")
    assert tx.import_status == ImportStatus.IMPORTED


@pytest.mark.asyncio
async def test_resolve_conflict_update_from_new_requires_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id))
    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": "UPDATE_FROM_NEW"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


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
