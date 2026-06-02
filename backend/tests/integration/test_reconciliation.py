from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.constants import ImportStatus, ReconciledStatus
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User


async def _create_transaction(
    client: AsyncClient,
    headers: dict[str, str],
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
    headers: dict[str, str],
    total: float = 100.0,
    paid: str = "2024-01-10T12:30:00",
    fn: str | None = None,
    counterparty_id: str | None = None,
) -> str:
    payload: dict = {
        "paid_at": paid,
        "total_amount": total,
        "fn": fn,
        "items": [{"name": "Item", "quantity": "1", "price": str(total), "amount": str(total)}],
    }
    if counterparty_id is not None:
        payload["counterparty_id"] = counterparty_id
    resp = await client.post("/api/v1/receipts", json=payload, headers=headers)
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
    tx_counterparty_id = tx_resp.json()["counterparty_id"]
    receipt_id = await _create_receipt(client, auth_headers, 100.0, "2024-01-10T12:30:00")
    await client.put(
        f"/api/v1/receipts/{receipt_id}",
        json={"counterparty_id": tx_counterparty_id},
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
async def test_manual_match_rejects_already_matched_transaction(
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
async def test_manual_match_rejects_transaction_with_existing_receipt_link(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    receipt_id_1 = await _create_receipt(client, auth_headers, fn="match-link-r1")
    receipt_id_2 = await _create_receipt(client, auth_headers, fn="match-link-r2")

    tx = session.get(Transaction, UUID(tx_id))
    assert tx is not None
    tx.receipt_id = UUID(receipt_id_1)
    tx.reconciled_status = ReconciledStatus.UNMATCHED
    session.add(tx)
    session.commit()

    resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id_2},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_manual_match_rejects_already_matched_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    first_tx_id = await _create_transaction(
        client, auth_headers, str(test_account.id), -100.0, "2024-01-10T12:00:00"
    )
    second_tx_id = await _create_transaction(
        client, auth_headers, str(test_account.id), -101.0, "2024-01-10T12:01:00"
    )
    receipt_id = await _create_receipt(client, auth_headers)

    first_resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": first_tx_id, "receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert first_resp.status_code == 200

    second_resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": second_tx_id, "receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert second_resp.status_code == 409


@pytest.mark.asyncio
async def test_ignore_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
) -> None:
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    resp = await client.post(
        "/api/v1/reconciliation/ignore",
        json={"transaction_id": tx_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    tx = session.get(Transaction, UUID(tx_id))
    session.refresh(tx)
    assert tx.reconciled_status == ReconciledStatus.IGNORED_BY_USER
    assert tx.receipt_id is None


@pytest.mark.parametrize(
    "has_match",
    [
        pytest.param(True, id="matched_via_api"),
        pytest.param(False, id="receipt_id_set_manually"),
    ],
)
@pytest.mark.asyncio
async def test_ignore_transaction_with_receipt_is_rejected(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
    has_match: bool,
) -> None:
    """Ignoring a transaction that already has a receipt linked must return 409."""
    tx_id = await _create_transaction(client, auth_headers, str(test_account.id))
    receipt_id = await _create_receipt(client, auth_headers, fn=f"ignore-guard-{has_match}")

    if has_match:
        match_resp = await client.post(
            "/api/v1/reconciliation/match",
            json={"transaction_id": tx_id, "receipt_id": receipt_id},
            headers=auth_headers,
        )
        assert match_resp.status_code == 200
    else:
        tx = session.get(Transaction, UUID(tx_id))
        tx.receipt_id = UUID(receipt_id)
        tx.reconciled_status = ReconciledStatus.UNMATCHED
        session.add(tx)
        session.commit()

    resp = await client.post(
        "/api/v1/reconciliation/ignore",
        json={"transaction_id": tx_id},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_collision_two_txs_one_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
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
    await _create_receipt(client, auth_headers, 999.99, "2024-06-01T10:00:00")

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    data = run_resp.json()
    assert data["summary"]["unmatched_receipts_count"] >= 1


@pytest.mark.asyncio
async def test_reconciliation_unmatched_receipts_ignores_other_user_transaction_links(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_test_user: User,
    session: Session,
) -> None:
    receipt_id = await _create_receipt(client, auth_headers, 333.0, "2024-01-10T12:30:00")
    other_account = Account(
        user_id=second_test_user.id,
        bank="OtherBank",
        account_number="40817810000000000002",
        currency="RUB",
    )
    session.add(other_account)
    session.flush()
    session.add(
        Transaction(
            account_id=other_account.id,
            occurred_at=datetime.fromisoformat("2024-01-10T12:00:00"),
            amount=-333.0,
            type="EXPENSE",
            receipt_id=UUID(receipt_id),
        )
    )
    session.commit()

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    assert run_resp.status_code == 200
    receipt_ids = {item["receipt_id"] for item in run_resp.json()["unmatched_receipts"]}
    assert receipt_id in receipt_ids


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


@pytest.mark.parametrize(
    "transaction_case, expected_status",
    [
        ("non_conflict", 409),
        ("nonexistent", 404),
    ],
)
@pytest.mark.asyncio
async def test_resolve_conflict_rejects_invalid_transaction_state(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    transaction_case: Literal["non_conflict", "nonexistent"],
    expected_status: int,
) -> None:
    tx_id = (
        await _create_transaction(client, auth_headers, str(test_account.id))
        if transaction_case == "non_conflict"
        else str(uuid4())
    )
    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": "KEEP_OLD"},
        headers=auth_headers,
    )
    assert resp.status_code == expected_status


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


@pytest.mark.parametrize(
    "match_case",
    [
        "nonexistent_transaction",
        "nonexistent_receipt",
        "other_user_receipt",
    ],
)
@pytest.mark.asyncio
async def test_manual_match_rejects_invalid_transaction_or_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
    test_account: Account,
    match_case: Literal["nonexistent_transaction", "nonexistent_receipt", "other_user_receipt"],
) -> None:
    tx_id = (
        str(uuid4())
        if match_case == "nonexistent_transaction"
        else await _create_transaction(client, auth_headers, str(test_account.id))
    )
    receipt_id = (
        await _create_receipt(client, second_auth_headers)
        if match_case == "other_user_receipt"
        else str(uuid4())
    )

    resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id},
        headers=auth_headers,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reconciliation_transaction_no_matching_receipt_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    # Transaction with unique amount, no receipt at that amount → missing_receipts
    await _create_transaction(client, auth_headers, str(test_account.id), -300.0)

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    data = run_resp.json()
    assert data["summary"]["missing_receipts_count"] >= 1
    assert data["summary"]["auto_matched_count"] == 0


@pytest.mark.asyncio
async def test_reconciliation_auto_match_with_counterparty(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
) -> None:
    # Both sides share same counterparty slug: score = 40 (time) + 40 (fuzzy-high) + 20 (single) = 100
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
    tx_id = tx_resp.json()["id"]
    tx_counterparty_id = tx_resp.json()["counterparty_id"]

    await _create_receipt(
        client, auth_headers, 100.0, "2024-01-10T12:30:00", counterparty_id=tx_counterparty_id
    )

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["summary"]["auto_matched_count"] == 1
    assert data["summary"]["missing_receipts_count"] == 0
    assert data["summary"]["unmatched_receipts_count"] == 0

    tx = session.get(Transaction, UUID(tx_id))
    assert tx is not None
    session.refresh(tx)
    assert tx.reconciled_status == ReconciledStatus.MATCHED


@pytest.mark.asyncio
async def test_reconciliation_outside_time_window(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    # tx occurred 9 days before receipt → outside the ±12h / +3d window
    await _create_transaction(
        client, auth_headers, str(test_account.id), -100.0, "2024-01-01T12:00:00"
    )
    await _create_receipt(client, auth_headers, 100.0, "2024-01-10T12:30:00")

    run_resp = await client.post("/api/v1/reconciliation/run", headers=auth_headers)
    data = run_resp.json()
    assert data["summary"]["auto_matched_count"] == 0
    assert data["summary"]["missing_receipts_count"] == 1
    assert data["summary"]["unmatched_receipts_count"] == 1


