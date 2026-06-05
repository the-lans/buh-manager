from collections.abc import Callable
from datetime import datetime
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
async def test_transaction_create_preserves_manual_expense_type_when_rule_matches(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session,
) -> None:
    from app.models.expense_type import ExpenseType
    from app.models.user import User
    from app.utils.ids import scope_user_id
    from sqlmodel import select

    user = session.exec(select(User).where(User.email == "test@example.com")).first()
    assert user is not None

    auto_et_public = "auto-et"
    auto_et_scoped = scope_user_id(user_id=user.id, public_id=auto_et_public)
    session.add(
        ExpenseType(
            id=auto_et_scoped,
            user_id=user.id,
            name="Auto category",
            receipt_required=False,
        )
    )
    session.commit()

    rule_resp = await client.post(
        "/api/v1/classifier-rules",
        json={
            "name": "Автоправило кофе",
            "expense_type_id": auto_et_public,
            "priority": 1,
            "is_active": True,
            "cond_bank_category": "кофе",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    create_resp = await client.post(
        "/api/v1/transactions",
        json={
            **_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
            "type": "EXPENSE",
            "bank_category": "Кофе и напитки",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["expense_type_id"] == test_expense_type_id


@pytest.mark.asyncio
async def test_transaction_update_preserves_manual_expense_type_when_rule_matches(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session,
) -> None:
    from app.models.expense_type import ExpenseType
    from app.models.user import User
    from app.utils.ids import scope_user_id
    from sqlmodel import select

    user = session.exec(select(User).where(User.email == "test@example.com")).first()
    assert user is not None

    auto_et_public = "auto-et-update"
    auto_et_scoped = scope_user_id(user_id=user.id, public_id=auto_et_public)
    session.add(
        ExpenseType(
            id=auto_et_scoped,
            user_id=user.id,
            name="Auto category update",
            receipt_required=False,
        )
    )
    session.commit()

    rule_resp = await client.post(
        "/api/v1/classifier-rules",
        json={
            "name": "Автоправило update",
            "expense_type_id": auto_et_public,
            "priority": 1,
            "is_active": True,
            "cond_bank_category": "кофе",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    create_resp = await client.post(
        "/api/v1/transactions",
        json={
            **_tx_payload(str(test_account.id), expense_type_id=test_expense_type_id),
            "type": "EXPENSE",
            "bank_category": "Еда",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    tx_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/transactions/{tx_id}",
        json={
            "expense_type_id": test_expense_type_id,
            "bank_category": "Кофе и напитки",
            "occurred_at": datetime(2024, 1, 10, 10, 0).isoformat(),
        },
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["expense_type_id"] == test_expense_type_id


@pytest.mark.asyncio
async def test_update_transaction_rejects_reconciled_status_override(
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
    assert update_resp.status_code == 422


@pytest.mark.asyncio
async def test_update_transaction_rejects_null_expense_type(
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
        json={"expense_type_id": None},
        headers=auth_headers,
    )
    assert update_resp.status_code == 422


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
            lambda _: _tx_payload(str(uuid4())),
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
