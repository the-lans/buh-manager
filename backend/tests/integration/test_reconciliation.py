from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.constants import ImportStatus, ReconciledStatus
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.utils.dt import utcnow
from tests.conftest import make_jwt


async def _create_transaction(
    client: AsyncClient,
    headers: dict,
    account_id: str,
    amount: float = -100.0,
    occurred: str = "2024-01-10T12:00:00",
) -> str:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "occurred_at": occurred,
            "amount": amount,
            "type": "EXPENSE",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_receipt(
    client: AsyncClient,
    headers: dict,
    total: float = 100.0,
    paid: str = "2024-01-10T12:30:00",
    fn: str | None = None,
) -> str:
    resp = await client.post(
        "/api/v1/receipts",
        json={
            "paid_at": paid,
            "total_amount": total,
            "fn": fn,
            "items": [{"name": "Item", "quantity": "1", "price": str(total), "amount": str(total)}],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_reconciliation_empty_db(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["auto_matched_count"] == 0
    assert data["summary"]["missing_receipts_count"] == 0


@pytest.mark.asyncio
async def test_reconciliation_1_to_1_auto_match(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    # Both parties share the same counterparty slug → high fuzzy score
    cp_resp = await client.post(
        "/api/v1/counterparties",
        json={"name": "Sberbank", "type": "COMPANY"},
        headers=auth_headers,
    )
    _ = cp_resp.json()["id"]

    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2024-01-10T12:00:00",
            "amount": -100.0,
            "type": "EXPENSE",
            "counterparty_name": "Sberbank",
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201
    receipt_id = await _create_receipt(client, auth_headers, 100.0, "2024-01-10T12:30:00")

    # Set receipt counterparty
    await client.put(
        f"/api/v1/receipts/{receipt_id}",
        json={"total_amount": 100.0, "paid_at": "2024-01-10T12:30:00"},
        headers=auth_headers,
    )

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    assert run_resp.status_code == 200
    assert "summary" in run_resp.json()


@pytest.mark.asyncio
async def test_reconciliation_get_last_report(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    resp = await client.get("/api/v1/reconciliation/report", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is not None


@pytest.mark.asyncio
async def test_reconciliation_report_before_run_returns_null(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get("/api/v1/reconciliation/report", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_manual_match(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    receipt_id = await _create_receipt(client, auth_headers)

    resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "matched"


@pytest.mark.asyncio
async def test_manual_match_rejects_other_user_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_account: Account,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))

    user_b = User(
        id=uuid4(),
        email="userB_match@example.com",
        full_name="User B",
        is_active=True,
        created_at=utcnow(),
    )
    session.add(user_b)
    session.commit()
    headers_b = {"Authorization": f"Bearer {make_jwt(str(user_b.id))}"}
    receipt_id = await _create_receipt(client, headers_b, fn="match-other-user")

    resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ignore_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    resp = await client.post(
        "/api/v1/reconciliation/ignore",
        json={"transaction_id": tx_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_collision_two_txs_one_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    # 2 transactions with same amount + 1 receipt → collision
    await _create_transaction(
        client, auth_headers, str(test_account.id), -200.0, "2024-01-05T10:00:00"
    )
    await _create_transaction(
        client, auth_headers, str(test_account.id), -200.0, "2024-01-05T11:00:00"
    )
    await _create_receipt(client, auth_headers, 200.0, "2024-01-05T10:30:00")

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    data = run_resp.json()
    assert data["summary"]["collisions_count"] >= 1


@pytest.mark.asyncio
async def test_unmatched_receipt_no_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # Receipt with no matching transaction → appears in unmatched_receipts
    await _create_receipt(client, auth_headers, 999.99, "2024-06-01T10:00:00")

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    data = run_resp.json()
    assert data["summary"]["unmatched_receipts_count"] >= 1


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        ({"action": "KEEP_OLD"}, "resolved"),
        ({"action": "UPDATE_FROM_NEW", "incoming_amount": "-101.00"}, "resolved"),
    ],
)
@pytest.mark.asyncio
async def test_resolve_conflict(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
    payload: dict[str, str],
    expected_status: str,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    tx = session.get(Transaction, UUID(tx_id))
    assert tx is not None
    tx.import_status = ImportStatus.CONFLICT
    session.add(tx)
    session.commit()

    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, **payload},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == expected_status


@pytest.mark.asyncio
async def test_resolve_conflict_nonexistent_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": str(uuid4()), "action": "KEEP_OLD"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.parametrize("status_code", [404])
@pytest.mark.asyncio
async def test_ignore_nonexistent_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
    status_code: int,
) -> None:
    resp = await client.post(
        "/api/v1/reconciliation/ignore",
        json={"transaction_id": str(uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == status_code


@pytest.mark.asyncio
async def test_manual_match_already_matched_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    receipt_id_1 = await _create_receipt(client, auth_headers, fn="match-409-r1")
    receipt_id_2 = await _create_receipt(client, auth_headers, fn="match-409-r2")

    first = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id_1},
        headers=auth_headers,
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id_2},
        headers=auth_headers,
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_ignore_clears_receipt_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    receipt_id = await _create_receipt(client, auth_headers, fn="ignore-clear-r1")

    match_resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert match_resp.status_code == 200

    ignore_resp = await client.post(
        "/api/v1/reconciliation/ignore",
        json={"transaction_id": tx_id},
        headers=auth_headers,
    )
    assert ignore_resp.status_code == 200

    tx = session.get(Transaction, UUID(tx_id))
    session.refresh(tx)
    assert tx is not None
    assert tx.receipt_id is None
    assert tx.reconciled_status == ReconciledStatus.IGNORED_BY_USER


@pytest.mark.asyncio
async def test_manual_match_nonexistent_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": str(uuid4()), "receipt_id": str(uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == 404
