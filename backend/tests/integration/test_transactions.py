from collections.abc import Callable
from typing import Literal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.models.account import Account


def _tx_payload(account_id: str, amount: float = -100.0, expense_type_id: str = "test-et") -> dict:
    return {
        "account_id": account_id,
        "occurred_at": "2024-01-10T10:00:00",
        "amount": amount,
        "type": "DEBIT",
        "expense_type_id": expense_type_id,
    }


@pytest.mark.asyncio
async def test_create_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    resp = await client.post(
        "/api/v1/transactions",
        json=_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["amount"]) == -100.0


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.asyncio
async def test_transaction_rejects_unknown_expense_type(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    operation: Literal["create", "update"],
) -> None:
    payload = {**_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id), "expense_type_id": "missing-expense-type"}
    if operation == "create":
        resp = await client.post("/api/v1/transactions", json=payload, headers=auth_headers)
    else:
        create_resp = await client.post(
            "/api/v1/transactions",
            json=_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        resp = await client.put(
            f"/api/v1/transactions/{create_resp.json()['id']}",
            json={"expense_type_id": "missing-expense-type"},
            headers=auth_headers,
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_transactions_with_filters(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    await client.post(
        "/api/v1/transactions",
        json={
            **_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
            "type": "DEBIT",
            "occurred_at": "2024-01-10T10:00:00",
        },
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/transactions",
        json={
            **_tx_payload(str(test_account.id), 500.0, expense_type_id=test_expense_type_id),
            "type": "INCOME",
            "occurred_at": "2024-01-11T10:00:00",
        },
        headers=auth_headers,
    )

    resp = await client.get(
        "/api/v1/transactions",
        headers=auth_headers,
        params={"type": "INCOME"},
    )
    assert resp.status_code == 200
    txs = resp.json()
    assert all(t["type"] == "INCOME" for t in txs)


@pytest.mark.asyncio
async def test_update_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/transactions",
        json=_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    tx_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/transactions/{tx_id}",
        json={"amount": -200.0, "occurred_at": "2024-01-10T10:00:00"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert float(update_resp.json()["amount"]) == -200.0


@pytest.mark.asyncio
async def test_update_transaction_reconciled_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/transactions",
        json=_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    tx_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/transactions/{tx_id}",
        json={"reconciled_status": "IGNORED_BY_USER"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["reconciled_status"] == "IGNORED_BY_USER"


@pytest.mark.asyncio
async def test_delete_transaction(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/transactions",
        json=_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    tx_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/transactions/{tx_id}", headers=auth_headers)
    assert del_resp.status_code == 204


@pytest.mark.parametrize(
    "method, path_fn, body_fn, expected_status",
    [
        pytest.param(
            "put",
            lambda _: f"/api/v1/transactions/{uuid4()}",
            lambda _: {"amount": -999.0, "occurred_at": "2024-01-10T10:00:00"},
            404,
            id="update_nonexistent_tx",
        ),
        pytest.param(
            "post",
            lambda _: "/api/v1/transactions",
            lambda account: _tx_payload(str(uuid4())),
            404,
            id="create_unknown_account",
        ),
    ],
)
@pytest.mark.asyncio
async def test_transaction_not_found_cases(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    method: str,
    path_fn: Callable,
    body_fn: Callable,
    expected_status: int,
) -> None:
    resp = await getattr(client, method)(
        path_fn(test_account),
        json=body_fn(test_account),
        headers=auth_headers,
    )
    assert resp.status_code == expected_status


@pytest.mark.asyncio
async def test_create_transaction_returns_valid_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    """create_transaction flushes internally so the response always contains a valid UUID id."""
    resp = await client.post(
        "/api/v1/transactions",
        json=_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    UUID(resp.json()["id"])
