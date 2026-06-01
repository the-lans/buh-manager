import io
from typing import Literal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.constants import DocumentStatus, DocumentType
from app.models.account import Account
from app.models.document import Document
from app.models.user import User
from app.utils.dt import utcnow
from tests.conftest import make_jwt


def _receipt_payload(
    fn: str | None = "1234567890",
    fd: str | None = "123456",
    fpd: str | None = "1234567890",
    counterparty: str | None = "Магазин Тест",
    total: float = 100.0,
) -> dict:
    return {
        "paid_at": "2024-01-15T12:00:00",
        "total_amount": total,
        "counterparty_name": counterparty,
        "fn": fn,
        "fd": fd,
        "fpd": fpd,
        "items": [
            {
                "name": "Товар 1",
                "quantity": "1",
                "price": str(total),
                "amount": str(total),
            }
        ],
    }


async def _create_doc(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (f"receipt_doc_{uuid4()}.pdf", io.BytesIO(uuid4().bytes), "application/pdf")
        },
        params={"doc_type": "RECEIPT"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["fn"] == "1234567890"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_fiscal_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    await client.post("/api/v1/receipts", json=_receipt_payload(), headers=auth_headers)
    resp = await client.post("/api/v1/receipts", json=_receipt_payload(), headers=auth_headers)
    assert resp.status_code == 409
    assert "receipt_id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_duplicate_fiscal_is_scoped_per_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
) -> None:
    payload = _receipt_payload(fn="5555555555", fd="555555", fpd="5555555555")
    resp_a = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert resp_a.status_code == 201

    user_b = User(
        id=uuid4(),
        email="userB_receipt_dedup@example.com",
        full_name="User B",
        is_active=True,
        created_at=utcnow(),
    )
    session.add(user_b)
    session.commit()
    headers_b = {"Authorization": f"Bearer {make_jwt(str(user_b.id))}"}

    resp_b = await client.post("/api/v1/receipts", json=payload, headers=headers_b)
    assert resp_b.status_code == 201
    assert resp_b.json()["id"] != resp_a.json()["id"]


@pytest.mark.asyncio
async def test_create_receipt_all_fiscal_null_no_dedup(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    payload = _receipt_payload(fn=None, fd=None, fpd=None)
    r1 = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    r2 = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]


@pytest.mark.asyncio
async def test_create_receipt_partial_fiscal_no_dedup(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # Only 2 of 3 fiscal fields → no dedup
    payload = _receipt_payload(fn="123", fd="456", fpd=None)
    r1 = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    r2 = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_update_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="9999999999", fd="999999", fpd="9999999999"),
        headers=auth_headers,
    )
    receipt_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/receipts/{receipt_id}",
        json={"total_amount": 200.0, "paid_at": "2024-01-16T10:00:00"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert float(update_resp.json()["total_amount"]) == 200.0


@pytest.mark.asyncio
async def test_delete_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="8888888888", fd="888888", fpd="8888888888"),
        headers=auth_headers,
    )
    receipt_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/receipts/{receipt_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/receipts/{receipt_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_receipt_linked_to_transaction_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    create_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="9999999999", fd="999999", fpd="9999999999"),
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    receipt_id = create_resp.json()["id"]

    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2024-01-15T11:30:00",
            "amount": -100.0,
            "type": "EXPENSE",
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201
    tx_id = tx_resp.json()["id"]

    match_resp = await client.post(
        "/api/v1/reconciliation/match",
        json={"transaction_id": tx_id, "receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert match_resp.status_code == 200

    del_resp = await client.delete(f"/api/v1/receipts/{receipt_id}", headers=auth_headers)
    assert del_resp.status_code == 409


@pytest.mark.asyncio
async def test_get_nonexistent_receipt_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get(f"/api/v1/receipts/{uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_access_user_a_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
) -> None:
    # User A creates a receipt via API (gets user_id set)
    create_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="7777777777", fd="777777", fpd="7777777777"),
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    receipt_id = create_resp.json()["id"]

    # Create user B and get their token
    user_b = User(
        id=uuid4(),
        email="userB_receipts@example.com",
        full_name="User B",
        is_active=True,
        created_at=utcnow(),
    )
    session.add(user_b)
    session.commit()
    headers_b = {"Authorization": f"Bearer {make_jwt(str(user_b.id))}"}

    # User B tries to access user A's receipt
    resp = await client.get(f"/api/v1/receipts/{receipt_id}", headers=headers_b)
    assert resp.status_code == 404


@pytest.mark.parametrize("document_case", ["nonexistent", "other_user"])
@pytest.mark.asyncio
async def test_create_receipt_with_invalid_document_id_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_test_user: User,
    session: Session,
    document_case: Literal["nonexistent", "other_user"],
) -> None:
    if document_case == "other_user":
        doc = Document(
            user_id=second_test_user.id,
            type=DocumentType.RECEIPT,
            url=f"/media/fake/{uuid4()}.pdf",
            name="foreign.pdf",
            status=DocumentStatus.PENDING,
            file_hash=f"foreign-doc-hash-{uuid4()}",
        )
        session.add(doc)
        session.commit()
        document_id = str(doc.id)
    else:
        document_id = str(uuid4())

    payload = _receipt_payload(fn=None, fd=None, fpd=None)
    payload["document_id"] = document_id

    resp = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_a_receipt_visible_in_own_list(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="6666666666", fd="666666", fpd="6666666666"),
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/receipts", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
