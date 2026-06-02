import pytest
from httpx import AsyncClient

from app.models.account import Account


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_accounts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_test_account: Account,
) -> None:
    resp = await client.get("/api/v1/accounts", headers=auth_headers)
    assert resp.status_code == 200
    ids = [a["id"] for a in resp.json()]
    assert str(second_test_account.id) not in ids


@pytest.mark.asyncio
async def test_user_a_cannot_update_user_b_account(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_test_account: Account,
) -> None:
    resp = await client.put(
        f"/api/v1/accounts/{second_test_account.id}",
        json={"bank": "HackedBank"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_create_tx_on_user_b_account(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_test_account: Account,
) -> None:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(second_test_account.id),
            "occurred_at": "2024-01-10T10:00:00",
            "amount": -100.0,
            "type": "DEBIT",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_transactions(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
    second_test_account: Account,
) -> None:
    # User B creates a transaction
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(second_test_account.id),
            "occurred_at": "2024-01-10T10:00:00",
            "amount": -500.0,
            "type": "DEBIT",
        },
        headers=second_auth_headers,
    )
    tx_id = tx_resp.json()["id"]

    # User A lists transactions — should not see user B's
    resp_a = await client.get("/api/v1/transactions", headers=auth_headers)
    ids_a = [t["id"] for t in resp_a.json()]
    assert tx_id not in ids_a


@pytest.mark.asyncio
async def test_user_a_cannot_see_or_modify_user_b_counterparties(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/counterparties",
        json={"name": "B Counterparty", "type": "COMPANY"},
        headers=second_auth_headers,
    )
    assert create_resp.status_code == 201
    counterparty_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/counterparties", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert counterparty_id not in ids

    update_resp = await client.put(
        f"/api/v1/counterparties/{counterparty_id}",
        json={"name": "Hacked"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 404

    delete_resp = await client.delete(
        f"/api/v1/counterparties/{counterparty_id}",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_see_or_modify_user_b_expense_types(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/expense-types",
        json={"id": "travel", "name": "Travel"},
        headers=second_auth_headers,
    )
    assert create_resp.status_code == 201

    list_resp = await client.get("/api/v1/expense-types", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert "travel" not in ids

    update_resp = await client.put(
        "/api/v1/expense-types/travel",
        json={"name": "Hacked"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 404

    delete_resp = await client.delete("/api/v1/expense-types/travel", headers=auth_headers)
    assert delete_resp.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_use_user_b_expense_type_in_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    create_resp = await client.post(
        "/api/v1/expense-types",
        json={"id": "office", "name": "Office"},
        headers=second_auth_headers,
    )
    assert create_resp.status_code == 201

    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2024-01-10T10:00:00",
            "amount": -100.0,
            "type": "DEBIT",
            "expense_type_id": "office",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_use_user_b_counterparty_in_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/counterparties",
        json={"name": "B Shop", "type": "STORE"},
        headers=second_auth_headers,
    )
    assert create_resp.status_code == 201
    counterparty_id = create_resp.json()["id"]

    resp = await client.post(
        "/api/v1/receipts",
        json={
            "paid_at": "2024-05-01T10:00:00",
            "total_amount": 500.0,
            "fn": "1234567890",
            "fd": "123456",
            "fpd": "1234567890",
            "counterparty_id": counterparty_id,
            "items": [{"name": "Товар", "quantity": "1", "price": "500", "amount": "500"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_exchange_rates(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/exchange-rates",
        json={
            "base_currency": "USD",
            "quote_currency": "RUB",
            "rate": "90.0",
            "recorded_at": "2024-01-01T12:00:00",
        },
        headers=second_auth_headers,
    )
    assert create_resp.status_code == 201

    resp = await client.get("/api/v1/exchange-rates/latest", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_users_can_have_same_expense_type_public_id_without_collision(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    resp_a = await client.post(
        "/api/v1/expense-types",
        json={"id": "shared", "name": "Shared A"},
        headers=auth_headers,
    )
    resp_b = await client.post(
        "/api/v1/expense-types",
        json={"id": "shared", "name": "Shared B"},
        headers=second_auth_headers,
    )

    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    assert resp_a.json()["id"] == "shared"
    assert resp_b.json()["id"] == "shared"


@pytest.mark.asyncio
async def test_users_can_have_same_counterparty_public_id_without_collision(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    resp_a = await client.post(
        "/api/v1/counterparties",
        json={"name": "Common Shop", "type": "STORE"},
        headers=auth_headers,
    )
    resp_b = await client.post(
        "/api/v1/counterparties",
        json={"name": "Common Shop", "type": "STORE"},
        headers=second_auth_headers,
    )

    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    assert resp_a.json()["id"] == "common-shop"
    assert resp_b.json()["id"] == "common-shop"
