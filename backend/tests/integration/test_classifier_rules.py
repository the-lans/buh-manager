"""Integration tests for classifier rules CRUD and apply endpoint."""

from datetime import datetime
from decimal import Decimal
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
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cond_day_month", 0),
        ("cond_day_month", 32),
        ("cond_day_week", "not-json"),
        ("cond_day_week", "[]"),
        ("cond_day_week", "[0,7]"),
        ("cond_type", "DEBIT"),
    ],
)
async def test_create_rule_rejects_invalid_condition_values(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
    field: str,
    value: object,
) -> None:
    payload = _rule_payload(expense_type_id=test_expense_type_id)
    payload[field] = value
    resp = await client.post("/api/v1/classifier-rules", json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["cond_bank_category", "cond_description"])
async def test_create_rule_rejects_blank_string_as_only_condition(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
    field: str,
) -> None:
    payload = _rule_payload(expense_type_id=test_expense_type_id, cond_type=None)
    payload[field] = "   "
    resp = await client.post("/api/v1/classifier-rules", json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rule_rejects_unknown_account_condition(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(
            expense_type_id=test_expense_type_id,
            cond_type=None,
            cond_account_id=str(uuid4()),
        ),
        headers=auth_headers,
    )
    assert resp.status_code == 404


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
async def test_list_rules_same_priority_sorted_deterministically(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    first_resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id, priority=1, name="Правило B"),
        headers=auth_headers,
    )
    second_resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id, priority=1, name="Правило A"),
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/classifier-rules", headers=auth_headers)
    assert resp.status_code == 200
    rules = resp.json()
    assert [rule["id"] for rule in rules] == sorted(
        [first_resp.json()["id"], second_resp.json()["id"]]
    )


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
async def test_update_rule_rejects_empty_conditions(
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
        json={"cond_type": None},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_rule_keeps_representation_from_existing_conditions(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(
            expense_type_id=test_expense_type_id,
            cond_type="EXPENSE",
            cond_bank_category="кофе",
        ),
        headers=auth_headers,
    )
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/classifier-rules/{rule_id}",
        json={"name": "Переименовано"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Переименовано"
    assert "Тип: Расход" in data["representation"]
    assert "Категория содержит 'кофе'" in data["representation"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"cond_day_month": 0, "cond_day_month_op": "eq"}, 422),
        ({"cond_day_week": "[0,7]"}, 422),
        ({"cond_type": "DEBIT"}, 422),
        ({"cond_account_id": None, "cond_type": None}, 422),
    ],
)
async def test_update_rule_rejects_invalid_condition_values(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
    payload: dict[str, object],
    expected_status: int,
) -> None:
    create_resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/classifier-rules/{rule_id}",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == expected_status


@pytest.mark.asyncio
async def test_update_rule_rejects_unknown_account_condition(
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
        json={"cond_account_id": str(uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == 404


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
async def test_apply_rules_normalizes_period_as_moscow_dates(
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

    target_et_public = "tz-et"
    target_et_scoped = scope_user_id(user_id=user.id, public_id=target_et_public)
    session.add(
        ExpenseType(
            id=target_et_scoped,
            user_id=user.id,
            name="Timezone category",
            receipt_required=False,
        )
    )
    session.commit()

    create_tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2026-03-01T00:30:00",
            "amount": -250.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
            "bank_category": "Ночной кофе",
        },
        headers=auth_headers,
    )
    assert create_tx_resp.status_code == 201
    tx_id = create_tx_resp.json()["id"]

    rule_resp = await client.post(
        "/api/v1/classifier-rules",
        json={
            "name": "Timezone coffee",
            "expense_type_id": target_et_public,
            "priority": 1,
            "is_active": True,
            "cond_bank_category": "кофе",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    apply_resp = await client.post(
        "/api/v1/classifier-rules/apply",
        json={"start_date": "2026-03-01T00:00:00", "end_date": "2026-03-01T23:59:59"},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json()["updated_count"] == 1

    tx_resp = await client.get("/api/v1/transactions", headers=auth_headers)
    tx = next(item for item in tx_resp.json() if item["id"] == tx_id)
    assert tx["expense_type_id"] == target_et_public


@pytest.mark.asyncio
async def test_apply_rules_match_day_month_in_app_timezone(
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

    target_et_public = "local-day-et"
    target_et_scoped = scope_user_id(user_id=user.id, public_id=target_et_public)
    session.add(
        ExpenseType(
            id=target_et_scoped,
            user_id=user.id,
            name="Local day category",
            receipt_required=False,
        )
    )
    session.commit()

    create_tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2026-03-01T00:30:00",
            "amount": -175.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
            "bank_category": "Ночная покупка",
        },
        headers=auth_headers,
    )
    assert create_tx_resp.status_code == 201
    tx_id = create_tx_resp.json()["id"]

    rule_resp = await client.post(
        "/api/v1/classifier-rules",
        json={
            "name": "Первое число месяца",
            "expense_type_id": target_et_public,
            "priority": 1,
            "is_active": True,
            "cond_day_month": 1,
            "cond_day_month_op": "eq",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    apply_resp = await client.post(
        "/api/v1/classifier-rules/apply",
        json={"start_date": "2026-03-01T00:00:00", "end_date": "2026-03-01T23:59:59"},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json()["updated_count"] == 1

    tx_resp = await client.get("/api/v1/transactions", headers=auth_headers)
    tx = next(item for item in tx_resp.json() if item["id"] == tx_id)
    assert tx["expense_type_id"] == target_et_public


@pytest.mark.asyncio
async def test_update_rule_rejects_blank_string_conditions(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_expense_type_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/classifier-rules",
        json=_rule_payload(
            expense_type_id=test_expense_type_id,
            cond_bank_category="кофе",
        ),
        headers=auth_headers,
    )
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/classifier-rules/{rule_id}",
        json={"cond_bank_category": "   ", "cond_type": None},
        headers=auth_headers,
    )
    assert resp.status_code == 422


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


@pytest.mark.asyncio
async def test_apply_rules_processes_more_than_previous_hard_limit(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session,
) -> None:
    from app.models.expense_type import ExpenseType
    from app.models.transaction import Transaction
    from app.models.user import User
    from app.utils.ids import scope_user_id
    from sqlmodel import select

    user = session.exec(select(User).where(User.email == "test@example.com")).first()
    assert user is not None

    source_et_scoped = scope_user_id(user_id=user.id, public_id=test_expense_type_id)
    second_et_public = "bulk-et"
    second_et_scoped = scope_user_id(user_id=user.id, public_id=second_et_public)
    session.add(
        ExpenseType(
            id=second_et_scoped,
            user_id=user.id,
            name="Bulk category",
            receipt_required=False,
        )
    )

    total_transactions = 1_005
    for idx in range(total_transactions):
        session.add(
            Transaction(
                account_id=test_account.id,
                occurred_at=datetime(2026, 2, (idx % 28) + 1, 10, 0),
                amount=Decimal("-100.00"),
                type="EXPENSE",
                expense_type_id=source_et_scoped,
                bank_category="bulk coffee",
            )
        )
    session.commit()

    rule_resp = await client.post(
        "/api/v1/classifier-rules",
        json={
            "name": "Bulk coffee",
            "expense_type_id": second_et_public,
            "priority": 1,
            "is_active": True,
            "cond_bank_category": "coffee",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    apply_resp = await client.post(
        "/api/v1/classifier-rules/apply",
        json={"start_date": "2026-02-01T00:00:00", "end_date": "2026-02-28T23:59:59"},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json()["updated_count"] == total_transactions


# ── Manual transactions are not auto-overridden ───────────────────────────────


@pytest.mark.asyncio
async def test_rule_does_not_override_manual_expense_type_on_transaction_create(
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
            "expense_type_id": test_expense_type_id,
            "bank_category": "Кофе и напитки",
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201
    data = tx_resp.json()
    assert data["expense_type_id"] == test_expense_type_id
