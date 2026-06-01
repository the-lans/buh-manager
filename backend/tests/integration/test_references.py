from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.account import Account

# ── Accounts ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crud_accounts(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # Create
    create_resp = await client.post(
        "/api/v1/accounts",
        json={"bank": "Сбербанк", "account_number": "40817810000000000099", "currency": "RUB"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    acc_id = create_resp.json()["id"]
    assert create_resp.json()["has_balances"] is False

    # Update
    update_resp = await client.put(
        f"/api/v1/accounts/{acc_id}",
        json={"bank": "Т-Банк"},  # noqa: RUF001
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["bank"] == "Т-Банк"  # noqa: RUF001

    # List
    list_resp = await client.get("/api/v1/accounts", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [a["id"] for a in list_resp.json()]
    assert acc_id in ids

    # Delete
    del_resp = await client.delete(f"/api/v1/accounts/{acc_id}", headers=auth_headers)
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_initialize_balance(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    resp = await client.post(
        f"/api/v1/accounts/{test_account.id}/initialize-balance",
        json={"amount": 5000.0, "recorded_at": "2024-01-01T00:00:00", "source": "OPENING"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["amount"]) == 5000.0

    # Idempotent upsert (same key → updates, no duplicate)
    resp2 = await client.post(
        f"/api/v1/accounts/{test_account.id}/initialize-balance",
        json={"amount": 6000.0, "recorded_at": "2024-01-01T00:00:00", "source": "OPENING"},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert float(resp2.json()["amount"]) == 6000.0


@pytest.mark.asyncio
async def test_initialize_balance_wrong_account_returns_403(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        f"/api/v1/accounts/{uuid4()}/initialize-balance",
        json={"amount": 100.0, "recorded_at": "2024-01-01T00:00:00", "source": "OPENING"},
        headers=auth_headers,
    )
    assert resp.status_code == 403


# ── Expense types ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crud_expense_types(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/expense-types",
        json={"id": "groceries", "name": "Продукты", "receipt_required": True},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201

    list_resp = await client.get("/api/v1/expense-types", headers=auth_headers)
    assert any(e["id"] == "groceries" for e in list_resp.json())

    update_resp = await client.put(
        "/api/v1/expense-types/groceries",
        json={"name": "Еда", "receipt_required": False},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Еда"

    del_resp = await client.delete("/api/v1/expense-types/groceries", headers=auth_headers)
    assert del_resp.status_code == 204


# ── Counterparties ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_counterparties_get_or_create(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    r1 = await client.post(
        "/api/v1/counterparties",
        json={"name": "ООО Ромашка", "type": "COMPANY"},  # noqa: RUF001
        headers=auth_headers,
    )
    r2 = await client.post(
        "/api/v1/counterparties",
        json={"name": "ООО Ромашка", "type": "COMPANY"},  # noqa: RUF001
        headers=auth_headers,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


# ── Exchange rates ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exchange_rates_latest(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    await client.post(
        "/api/v1/exchange-rates",
        json={
            "base_currency": "USD",
            "quote_currency": "RUB",
            "rate": "90.0",
            "recorded_at": "2024-01-01T12:00:00",
        },
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/exchange-rates",
        json={
            "base_currency": "USD",
            "quote_currency": "RUB",
            "rate": "91.5",
            "recorded_at": "2024-01-02T12:00:00",
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/exchange-rates/latest", headers=auth_headers)
    assert resp.status_code == 200
    rates = resp.json()
    usd_rates = [r for r in rates if r["base_currency"] == "USD" and r["quote_currency"] == "RUB"]
    assert len(usd_rates) == 1
    assert float(usd_rates[0]["rate"]) == 91.5
