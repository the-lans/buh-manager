import io
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.account import Account


async def _create_stmt_doc(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": (f"stmt_{uuid4()}.pdf", io.BytesIO(uuid4().bytes), "application/pdf")},
        params={"doc_type": "BANK_STATEMENT"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _import_statement(
    client: AsyncClient,
    headers: dict,
    account_id: str,
    doc_id: str,
    expense_type_id: str,
    *,
    opening: float = 1000.0,
    closing: float = 900.0,
) -> None:
    payload = {
        "document_id": doc_id,
        "account_id": account_id,
        "statement_start": "2024-04-01T00:00:00",
        "statement_end": "2024-04-30T23:59:59",
        "opening_balance": opening,
        "closing_balance": closing,
        "transactions": [{"occurred_at": "2024-04-10T10:00:00", "amount": -100.0, "type": "DEBIT", "expense_type_id": expense_type_id}],
    }
    resp = await client.post("/api/v1/bank-statements", json=payload, headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_balances_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get("/api/v1/balances", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_balances_after_import(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(client, auth_headers, str(test_account.id), doc_id, test_expense_type_id)

    resp = await client.get("/api/v1/balances", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2  # opening + closing
    sources = {b["source"] for b in data}
    assert sources == {"OPENING", "CLOSING"}


@pytest.mark.asyncio
async def test_list_balances_filter_by_account(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(client, auth_headers, str(test_account.id), doc_id, test_expense_type_id)

    # Create second account with no balances
    acc2_resp = await client.post(
        "/api/v1/accounts",
        json={"bank": "Other", "account_number": "40817810000000000088"},
        headers=auth_headers,
    )
    acc2_id = acc2_resp.json()["id"]

    resp = await client.get(
        "/api/v1/balances",
        headers=auth_headers,
        params={"account_id": str(test_account.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(b["account_id"] == str(test_account.id) for b in data)

    # Filter by second account → empty
    resp2 = await client.get(
        "/api/v1/balances",
        headers=auth_headers,
        params={"account_id": acc2_id},
    )
    assert resp2.status_code == 200
    assert resp2.json() == []


@pytest.mark.asyncio
async def test_list_balances_other_user_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(client, auth_headers, str(test_account.id), doc_id, test_expense_type_id)

    resp = await client.get("/api/v1/balances", headers=second_auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_balances_ordered_newest_first(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    # Import two statements with different date ranges
    for month_start, month_end in [
        ("2024-01-01T00:00:00", "2024-01-31T23:59:59"),
        ("2024-03-01T00:00:00", "2024-03-31T23:59:59"),
    ]:
        doc_id = await _create_stmt_doc(client, auth_headers)
        payload = {
            "document_id": doc_id,
            "account_id": str(test_account.id),
            "statement_start": month_start,
            "statement_end": month_end,
            "opening_balance": 1000.0,
            "closing_balance": 900.0,
            "transactions": [],
        }
        resp = await client.post("/api/v1/bank-statements", json=payload, headers=auth_headers)
        assert resp.status_code == 200

    resp = await client.get(
        "/api/v1/balances",
        headers=auth_headers,
        params={"account_id": str(test_account.id)},
    )
    assert resp.status_code == 200
    dates = [b["recorded_at"] for b in resp.json()]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_calculate_balances_creates_manual_balance(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    # Seed an opening balance
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(client, auth_headers, str(test_account.id), doc_id, test_expense_type_id)

    # POST /balances/calculate
    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["source"] == "MANUAL"
    # opening=1000, closing=900 → last balance is 900, no new txs → calculated = 900
    assert float(results[0]["amount"]) == pytest.approx(900.0)


@pytest.mark.asyncio
async def test_calculate_balances_idempotent(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(client, auth_headers, str(test_account.id), doc_id, test_expense_type_id)

    await client.post("/api/v1/balances/calculate", headers=auth_headers)
    await client.post("/api/v1/balances/calculate", headers=auth_headers)

    # Only one MANUAL record for today should exist
    all_balances = await client.get(
        "/api/v1/balances",
        headers=auth_headers,
        params={"account_id": str(test_account.id), "limit": 100},
    )
    manual_records = [b for b in all_balances.json() if b["source"] == "MANUAL"]
    # The two calculate calls land on the same date → upsert → still 1 MANUAL record
    assert len(manual_records) == 1


@pytest.mark.asyncio
async def test_calculate_balances_includes_new_transactions(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    # Seed closing balance of 900 via import (opening 1000, one -100 tx)
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(client, auth_headers, str(test_account.id), doc_id, test_expense_type_id)

    # Add a manual transaction AFTER the last imported balance (closing recorded_at = statement_end)
    acc_resp = await client.get("/api/v1/accounts", headers=auth_headers)
    acc_id = str(test_account.id)
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": acc_id,
            "occurred_at": "2025-01-01T00:00:00",
            "amount": -250.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201

    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    # closing balance 900 + new tx -250 = 650
    assert float(results[0]["amount"]) == pytest.approx(650.0)


@pytest.mark.asyncio
async def test_calculate_balances_skips_account_without_balance(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    # Account exists but has NO balance records at all
    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    # Should return empty list — no account had a starting balance
    assert resp.json() == []
