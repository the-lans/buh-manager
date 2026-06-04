"""T79: Conflict resolution parametrized tests."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.constants import ImportStatus
from app.models.account import Account
from app.models.transaction import Transaction


async def _make_tx(client: AsyncClient, headers: dict[str, str], account_id: str, expense_type_id: str) -> str:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "occurred_at": "2024-03-01T10:00:00",
            "amount": -50.0,
            "type": "EXPENSE",
            "expense_type_id": expense_type_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _mark_conflict(session: Session, tx_id: str) -> Transaction:
    tx = session.get(Transaction, UUID(tx_id))
    assert tx is not None
    tx.import_status = ImportStatus.CONFLICT
    session.add(tx)
    session.commit()
    return tx


@pytest.mark.asyncio
async def test_resolve_conflict_keep_old_preserves_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id), test_expense_type_id)
    tx = await _mark_conflict(session, tx_id)

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
    test_expense_type_id: str,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id), test_expense_type_id)
    tx = await _mark_conflict(session, tx_id)

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
async def test_resolve_conflict_recalculates_downstream_balances(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    doc_resp = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("statement.pdf", b"stmt", "application/pdf")},
        params={"doc_type": "BANK_STATEMENT"},
    )
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["id"]

    import_resp = await client.post(
        "/api/v1/bank-statements",
        json={
            "document_id": doc_id,
            "account_id": str(test_account.id),
            "statement_start": "2024-03-01T00:00:00",
            "statement_end": "2024-03-31T23:59:59",
            "opening_balance": "1000.00",
            "closing_balance": "850.00",
            "transactions": [
                {
                    "occurred_at": "2024-03-01T10:00:00",
                    "amount": "-50.00",
                    "type": "DEBIT",
                    "expense_type_id": test_expense_type_id,
                    "balance_after": "950.00",
                },
                {
                    "occurred_at": "2024-03-01T11:00:00",
                    "amount": "-100.00",
                    "type": "DEBIT",
                    "expense_type_id": test_expense_type_id,
                    "balance_after": "850.00",
                },
            ],
        },
        headers=auth_headers,
    )
    assert import_resp.status_code == 200

    txs = session.exec(
        select(Transaction)
        .where(Transaction.account_id == test_account.id)
        .order_by(Transaction.occurred_at.asc(), Transaction.id.asc())
    ).all()
    assert len(txs) == 2
    txs[0].import_status = ImportStatus.CONFLICT
    session.add(txs[0])
    session.commit()

    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={
            "transaction_id": str(txs[0].id),
            "action": "UPDATE_FROM_NEW",
            "incoming_amount": "-75.00",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    session.refresh(txs[0])
    session.refresh(txs[1])
    assert txs[0].calculated_balance_after == Decimal("925.00")
    assert txs[0].balance_mismatch is True
    assert txs[1].calculated_balance_after == Decimal("825.00")
    assert txs[1].balance_mismatch is True


@pytest.mark.asyncio
async def test_resolve_conflict_update_from_new_requires_amount(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id), test_expense_type_id)
    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": "UPDATE_FROM_NEW"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        ({"transaction_id": str(uuid4()), "action": "KEEP_OLD"}, 404),
        ({"action": "KEEP_OLD"}, 409),
        ({"action": "UPDATE_FROM_NEW", "incoming_amount": "-50.0"}, 409),
    ],
)
@pytest.mark.asyncio
async def test_resolve_conflict_rejects_invalid_transaction_state(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    payload: dict[str, str],
    expected_status: int,
) -> None:
    if "transaction_id" not in payload:
        tx_id = await _make_tx(client, auth_headers, str(test_account.id), test_expense_type_id)
        payload = {"transaction_id": tx_id, **payload}

    resp = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == expected_status


@pytest.mark.asyncio
async def test_resolve_conflict_already_resolved_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    tx_id = await _make_tx(client, auth_headers, str(test_account.id), test_expense_type_id)
    await _mark_conflict(session, tx_id)
    first = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": "KEEP_OLD"},
        headers=auth_headers,
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/reconciliation/resolve-conflict",
        json={"transaction_id": tx_id, "action": "KEEP_OLD"},
        headers=auth_headers,
    )
    assert second.status_code == 409
