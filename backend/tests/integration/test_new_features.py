"""Tests for new features added in the UI/backend improvements PR:
- payload field on Counterparty
- payload field on Document (PUT /documents/{id})
- document_id filter on GET /receipts
- receipt_id, document_id and expense_type_id fields in TransactionListItem
- description field on ExpenseType
"""

import io
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.models.account import Account
from app.models.transaction import Transaction

# ── helpers ────────────────────────────────────────────────────────────────────


def _cp(name: str = "Тест Магазин", **kwargs: object) -> dict[str, object]:
    return {"name": name, "type": "STORE", **kwargs}


def _receipt_payload(total: float = 99.0) -> dict[str, object]:
    return {
        "paid_at": "2024-05-01T10:00:00",
        "total_amount": total,
        "fn": str(uuid4().int)[:10],
        "fd": str(uuid4().int)[:6],
        "fpd": str(uuid4().int)[:10],
        "items": [{"name": "X", "quantity": "1", "price": str(total), "amount": str(total)}],
    }


async def _upload_doc(
    client: AsyncClient,
    headers: dict[str, str],
    doc_type: str = "RECEIPT",
) -> str:
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": (f"f_{uuid4()}.pdf", io.BytesIO(uuid4().bytes), "application/pdf")},
        params={"doc_type": doc_type},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Counterparty payload ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_counterparty_with_payload(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    payload = {"адрес": "ул. Ленина 1", "сайт": "example.com"}
    resp = await client.post(
        "/api/v1/counterparties",
        json=_cp(name="Counterparty Payload", payload=payload),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["payload"] == payload


@pytest.mark.asyncio
async def test_counterparty_payload_null_by_default(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/counterparties",
        json=_cp(name="NoPayload"),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["payload"] is None


@pytest.mark.asyncio
async def test_update_counterparty_payload(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/counterparties",
        json=_cp(name="Обновляемый"),
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    cp_id = create_resp.json()["id"]

    new_payload = {"инн": "1234567890", "адрес": "Москва"}
    update_resp = await client.put(
        f"/api/v1/counterparties/{cp_id}",
        json={"name": "Обновляемый", "type": "STORE", "payload": new_payload},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["payload"] == new_payload


@pytest.mark.asyncio
async def test_update_counterparty_clears_payload(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/counterparties",
        json=_cp(name="WithPayload", payload={"key": "value"}),
        headers=auth_headers,
    )
    cp_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/counterparties/{cp_id}",
        json={"name": "WithPayload", "type": "STORE", "payload": None},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["payload"] is None


@pytest.mark.asyncio
async def test_list_counterparties_includes_payload(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    payload = {"email": "info@test.ru"}
    await client.post(
        "/api/v1/counterparties",
        json=_cp(name="PayloadInList", payload=payload),
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/counterparties", headers=auth_headers)
    assert resp.status_code == 200
    item = next(c for c in resp.json() if c["name"] == "PayloadInList")
    assert item["payload"] == payload


# ── Document payload (PUT /documents/{id}) ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_document_includes_payload_null(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _upload_doc(client, auth_headers)
    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["payload"] is None


@pytest.mark.asyncio
async def test_update_document_payload(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _upload_doc(client, auth_headers)
    new_payload = {"дата": "2024-05-01", "сумма": "1500.00", "продавец": "Магазин"}
    resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"payload": new_payload},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["payload"] == new_payload


@pytest.mark.asyncio
async def test_update_document_payload_reflected_in_get(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _upload_doc(client, auth_headers)
    payload = {"items": [{"name": "A", "qty": 2}]}
    await client.put(f"/api/v1/documents/{doc_id}", json={"payload": payload}, headers=auth_headers)

    get_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["payload"] == payload


@pytest.mark.asyncio
async def test_update_document_payload_clears_to_null(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _upload_doc(client, auth_headers)
    await client.put(
        f"/api/v1/documents/{doc_id}", json={"payload": {"x": 1}}, headers=auth_headers
    )
    resp = await client.put(
        f"/api/v1/documents/{doc_id}", json={"payload": None}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["payload"] is None


@pytest.mark.asyncio
async def test_update_document_not_found_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.put(
        f"/api/v1/documents/{uuid4()}",
        json={"payload": {"key": "val"}},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_document_other_user_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    doc_id = await _upload_doc(client, auth_headers)
    resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"payload": {"x": 1}},
        headers=second_auth_headers,
    )
    assert resp.status_code == 404


# ── GET /receipts?document_id= filter ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_receipts_filter_by_document_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _upload_doc(client, auth_headers, doc_type="RECEIPT")

    # Receipt linked to doc
    linked_resp = await client.post(
        "/api/v1/receipts",
        json={**_receipt_payload(), "document_id": doc_id},
        headers=auth_headers,
    )
    assert linked_resp.status_code == 201

    # Unlinked receipt
    await client.post("/api/v1/receipts", json=_receipt_payload(), headers=auth_headers)

    resp = await client.get(
        "/api/v1/receipts",
        headers=auth_headers,
        params={"document_id": doc_id},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["document_id"] == doc_id


@pytest.mark.asyncio
async def test_list_receipts_filter_by_nonexistent_document_returns_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    await client.post("/api/v1/receipts", json=_receipt_payload(), headers=auth_headers)

    resp = await client.get(
        "/api/v1/receipts",
        headers=auth_headers,
        params={"document_id": str(uuid4())},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_receipts_without_document_id_returns_all(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _upload_doc(client, auth_headers, doc_type="RECEIPT")
    await client.post(
        "/api/v1/receipts",
        json={**_receipt_payload(), "document_id": doc_id},
        headers=auth_headers,
    )
    await client.post("/api/v1/receipts", json=_receipt_payload(), headers=auth_headers)

    resp = await client.get("/api/v1/receipts", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── TransactionListItem includes receipt_id and document_id ───────────────────


@pytest.mark.asyncio
async def test_transaction_list_includes_receipt_id_and_document_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2024-05-01T10:00:00",
            "amount": -200.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201

    list_resp = await client.get("/api/v1/transactions", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert "receipt_id" in items[0]
    assert "document_id" in items[0]
    assert "expense_type_id" in items[0]
    assert "bank_category" in items[0]
    assert items[0]["receipt_id"] is None
    assert items[0]["document_id"] is None
    assert items[0]["expense_type_id"] == test_expense_type_id


@pytest.mark.asyncio
async def test_transaction_list_receipt_id_populated_after_linking(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
) -> None:
    """After reconciliation links a receipt, receipt_id appears in list items."""
    # Create a transaction
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2024-05-01T10:00:00",
            "amount": -99.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )
    tx_id = tx_resp.json()["id"]

    # Create a receipt
    receipt_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(total=99.0),
        headers=auth_headers,
    )
    receipt_id = receipt_resp.json()["id"]

    tx = session.get(Transaction, UUID(tx_id))
    assert tx is not None
    tx.receipt_id = UUID(receipt_id)
    session.add(tx)
    session.commit()

    list_resp = await client.get("/api/v1/transactions", headers=auth_headers)
    assert list_resp.status_code == 200
    item = next(t for t in list_resp.json() if t["id"] == tx_id)
    assert item["receipt_id"] == receipt_id


# ── ExpenseType description field ─────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "description,expected",
    [
        ("Расходы на продукты питания", "Расходы на продукты питания"),
        (None, None),
    ],
)
async def test_create_expense_type_description(
    client: AsyncClient,
    auth_headers: dict[str, str],
    description: str | None,
    expected: str | None,
) -> None:
    resp = await client.post(
        "/api/v1/expense-types",
        json={"id": f"et-desc-{uuid4().hex[:6]}", "name": "Тест", "description": description},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == expected


@pytest.mark.asyncio
async def test_update_expense_type_description(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/expense-types",
        json={"id": f"et-upd-{uuid4().hex[:6]}", "name": "Без описания"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    et_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/expense-types/{et_id}",
        json={"description": "Новое описание"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Новое описание"


@pytest.mark.asyncio
async def test_update_expense_type_description_clears_to_null(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/expense-types",
        json={"id": f"et-clr-{uuid4().hex[:6]}", "name": "Тип для очистки", "description": "Было"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    et_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/expense-types/{et_id}",
        json={"description": None},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] is None


@pytest.mark.asyncio
async def test_list_expense_types_includes_description(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    desc = "Описание для списка"
    await client.post(
        "/api/v1/expense-types",
        json={"id": f"et-lst-{uuid4().hex[:6]}", "name": "Листинг", "description": desc},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/expense-types", headers=auth_headers)
    assert resp.status_code == 200
    item = next(t for t in resp.json() if t["name"] == "Листинг")
    assert item["description"] == desc
