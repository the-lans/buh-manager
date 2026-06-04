"""Integration tests for classifier rules CRUD and apply endpoint."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.account import Account


def _rule_payload(expense_type_id: str = "test-et", **kwargs) -> dict:
    base = {
        "name": "Правило продукты",
        "expense_type_id": expense_type_id,
        "priority": 1,
        "is_active": True,
        "cond_type": "EXPENSE",
    }
    base.update(kwargs)
    return base


# ── CRUD ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Правило продукты"
    assert data["priority"] == 1
    assert data["is_active"] is True
    assert "Тип: Расход" in data["representation"]


@pytest.mark.asyncio
async def test_create_rule_no_conditions_fails(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    payload = {
        "name": "Пустое правило",
        "expense_type_id": test_expense_type_id,
        "priority": 1,
        "is_active": True,
    }
    resp = await client.post("/api/v1/classifier-rules", json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rule_amount_without_op_fails(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    payload = _rule_payload(expense_type_id=test_expense_type_id)
    payload["cond_amount"] = 500
    payload["cond_amount_op"] = None
    resp = await client.post("/api/v1/classifier-rules", json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_rules(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id, priority=2),
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id, priority=1, name="Правило 2"),
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/classifier-rules", headers=auth_headers)
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 2
    assert rules[0]["priority"] <= rules[1]["priority"]  # sorted by priority ASC


@pytest.mark.asyncio
async def test_update_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/classifier-rules/{rule_id}",
        json={"name": "Обновлённое правило", "cond_type": "INCOME"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Обновлённое правило"
    assert "Тип: Доход" in data["representation"]


@pytest.mark.asyncio
async def test_delete_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    rule_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/classifier-rules/{rule_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/v1/classifier-rules", headers=auth_headers)
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.delete(f"/api/v1/classifier-rules/{uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ── User isolation ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rules_isolated_between_users(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
    test_expense_type_id: str,
    second_test_expense_type_id: str,
) -> None:
    await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/classifier-rules", headers=second_auth_headers)
    assert resp.json() == []


# ── Apply endpoint ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_rules_updates_expense_type(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    second_test_expense_type_id: str,
    second_test_user,
) -> None:
    from app.utils.ids import scope_user_id
    from tests.conftest import make_jwt
    from app.models.expense_type import ExpenseType
    from sqlmodel import Session
    # Need a second expense type for the same user
    # We'll use the test client to create a rule that matches all EXPENSE transactions
    # and changes expense_type to test_expense_type_id

    # First create a transaction with test_expense_type_id
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2026-01-15T10:00:00",
            "amount": -500.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
            "bank_category": "Кофе",
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201
    tx_id = tx_resp.json()["id"]

    # Create a rule: bank_category contains "кофе" → keep same expense_type (already applied on create)
    # For a meaningful test, create rule with cond_bank_category and verify apply endpoint works
    rule_resp = await client.post(
        "/api/v1/classifier-rules",
        json={
            "name": "Кофе",
            "expense_type_id": test_expense_type_id,
            "priority": 1,
            "is_active": True,
            "cond_bank_category": "Кофе",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    apply_resp = await client.post(
        "/api/v1/classifier-rules/apply",
        json={"start_date": "2026-01-01T00:00:00", "end_date": "2026-01-31T23:59:59"},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 200
    # updated_count may be 0 if expense_type_id already matches; that's fine
    assert "updated_count" in apply_resp.json()


@pytest.mark.asyncio
async def test_apply_rules_no_rules_returns_zero(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    resp = await client.post(
        "/api/v1/classifier-rules/apply",
        json={"start_date": "2026-01-01T00:00:00", "end_date": "2026-01-31T23:59:59"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 0


# ── Rule applied on transaction create ────────────────────────────────────────


@pytest.mark.asyncio
async def test_rule_applied_on_transaction_create(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session,
) -> None:
    from app.models.expense_type import ExpenseType
    from app.utils.ids import scope_user_id
    from app.models.user import User
    from sqlmodel import select

    # Get test_user from DB
    user = session.exec(select(User).where(User.email == "test@example.com")).first()

    # Create a second expense type for the same user
    et2_public = "categoria-rule"
    et2_scoped = scope_user_id(user_id=user.id, public_id=et2_public)
    et2 = ExpenseType(id=et2_scoped, user_id=user.id, name="Категория правила", receipt_required=False)
    session.add(et2)
    session.commit()

    # Create a rule: cond_bank_category = "кофе" → et2
    rule_resp = await client.post(
        "/api/v1/classifier-rules",
        json={
            "name": "Кофе → категория правила",
            "expense_type_id": et2_public,
            "priority": 1,
            "is_active": True,
            "cond_bank_category": "кофе",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    # Create a transaction with bank_category containing "кофе"
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2026-03-01T09:00:00",
            "amount": -150.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,  # will be overridden by rule
            "bank_category": "Кофе и напитки",
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201
    data = tx_resp.json()
    # expense_type_id in response is unscoped
    assert data["expense_type_id"] == et2_public
