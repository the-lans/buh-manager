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
        "transactions": [
            {
                "occurred_at": "2024-04-10T10:00:00",
                "amount": -100.0,
                "type": "DEBIT",
                "expense_type_id": expense_type_id,
            }
        ],
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
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

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
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

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
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

    resp = await client.get("/api/v1/balances", headers=second_auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_calculate_balances_skips_when_amount_unchanged(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    """POST /balances/calculate must NOT write a new record when the computed
    amount equals the latest stored balance."""
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

    # No new transactions → balance unchanged → returns empty list
    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == [], "Should return empty list when balance is unchanged"

    # Verify no extra MANUAL record was created
    balances_resp = await client.get("/api/v1/balances", headers=auth_headers)
    sources = [b["source"] for b in balances_resp.json()]
    assert "MANUAL" not in sources


@pytest.mark.asyncio
async def test_calculate_balances_writes_when_amount_changed(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    """POST /balances/calculate writes a MANUAL record only when the balance changed."""
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

    # Add a transaction that changes the balance
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2024-05-01T12:00:00",
            "amount": "-50.00",
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )

    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source"] == "MANUAL"


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
    # Seed a closing balance of 900 via import
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

    # Add a new transaction AFTER the imported statement period — this changes the balance
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2025-01-01T00:00:00",
            "amount": -50.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )

    # POST /balances/calculate — amount changed, so a MANUAL record is written
    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["source"] == "MANUAL"
    # closing=900, new tx=-50 → 850
    assert float(results[0]["amount"]) == pytest.approx(850.0)


@pytest.mark.asyncio
async def test_calculate_balances_idempotent(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

    # Add a transaction to trigger a balance change on the first call
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2025-01-01T00:00:00",
            "amount": -50.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )

    # First calculate → writes MANUAL record (amount changed)
    await client.post("/api/v1/balances/calculate", headers=auth_headers)
    # Second calculate → amount unchanged since first call → skips write
    await client.post("/api/v1/balances/calculate", headers=auth_headers)

    # Only one MANUAL record should exist
    all_balances = await client.get(
        "/api/v1/balances",
        headers=auth_headers,
        params={"account_id": str(test_account.id), "limit": 100},
    )
    manual_records = [b for b in all_balances.json() if b["source"] == "MANUAL"]
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
    await _import_statement(
        client, auth_headers, str(test_account.id), doc_id, test_expense_type_id
    )

    # Add a manual transaction AFTER the last imported balance (closing recorded_at = statement_end)
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
) -> None:
    # Account exists but has NO balance records at all
    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    # Should return empty list — no account had a starting balance
    assert resp.json() == []


@pytest.mark.asyncio
async def test_calculate_balances_uses_account_zero_balance_without_balance_records(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    account_resp = await client.post(
        "/api/v1/accounts",
        json={
            "bank": "Zero Bank",
            "account_number": "0001",
            "currency": "RUB",
            "zero_balance": "1000.00",
        },
        headers=auth_headers,
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "occurred_at": "2024-05-01T12:00:00",
            "amount": "-150.00",
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201

    resp = await client.post("/api/v1/balances/calculate", headers=auth_headers)
    assert resp.status_code == 200
    results = [row for row in resp.json() if row["account_id"] == account_id]

    assert len(results) == 1
    assert results[0]["source"] == "MANUAL"
    assert float(results[0]["amount"]) == pytest.approx(850.0)
