import io
from typing import Any, Literal, cast
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.constants import DocumentStatus, DocumentType
from app.db import receipts as receipts_db
from app.models.account import Account
from app.models.counterparty import Counterparty
from app.models.document import Document
from app.models.receipt import Receipt
from app.models.user import User
from app.routers import receipts as receipts_router
from app.utils.dt import utcnow
from app.utils.ids import scope_user_id
from tests.conftest import make_jwt


def _receipt_payload(
    fn: str | None = "1234567890",
    fd: str | None = "123456",
    fpd: str | None = "1234567890",
    counterparty_id: str | None = None,
    total: float = 100.0,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "paid_at": "2024-01-15T12:00:00",
        "total_amount": total,
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
    if counterparty_id is not None:
        payload["counterparty_id"] = counterparty_id
    return payload


async def _create_doc(
    client: AsyncClient,
    headers: dict[str, str],
    doc_type: str = "RECEIPT",
) -> str:
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (f"receipt_doc_{uuid4()}.pdf", io.BytesIO(uuid4().bytes), "application/pdf")
        },
        params={"doc_type": doc_type},
    )
    assert resp.status_code == 201
    return cast("str", resp.json()["id"])


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


@pytest.mark.parametrize("max_age_days", ["-1", "3651"])
@pytest.mark.asyncio
async def test_list_receipts_rejects_invalid_max_age_days(
    client: AsyncClient,
    auth_headers: dict[str, str],
    max_age_days: str,
) -> None:
    resp = await client.get(
        "/api/v1/receipts",
        params={"max_age_days": max_age_days},
        headers=auth_headers,
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_duplicate_fiscal_race_returns_409_from_db_constraint(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _receipt_payload(fn="1234500000", fd="987654", fpd="1234509876")
    first = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert first.status_code == 201

    original = receipts_db.get_receipt_by_fiscal
    calls = 0

    def bypass_precheck(
        *,
        session: Session,
        fn: str,
        fd: str,
        fpd: str,
        user_id: UUID,
        exclude_receipt_id: UUID | None = None,
    ) -> Receipt | None:
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return original(
            session=session,
            fn=fn,
            fd=fd,
            fpd=fpd,
            user_id=user_id,
            exclude_receipt_id=exclude_receipt_id,
        )

    monkeypatch.setattr(receipts_router, "get_receipt_by_fiscal", bypass_precheck)

    second = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)

    assert second.status_code == 409
    assert "receipt_id" in second.json()["detail"]
    receipts = session.exec(select(Receipt).where(Receipt.fn == "1234500000")).all()
    assert len(receipts) == 1


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
async def test_update_receipt_to_duplicate_fiscal_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    first = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="1111222233", fd="101010", fpd="9999000011"),
        headers=auth_headers,
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="2222333344", fd="202020", fpd="8888777766"),
        headers=auth_headers,
    )
    assert second.status_code == 201

    update_resp = await client.put(
        f"/api/v1/receipts/{second.json()['id']}",
        json={"fn": "1111222233", "fd": "101010", "fpd": "9999000011"},
        headers=auth_headers,
    )

    assert update_resp.status_code == 409
    assert "receipt_id" in update_resp.json()["detail"]


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
    test_expense_type_id: str,
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
            "expense_type_id": test_expense_type_id,
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


@pytest.mark.parametrize("scenario", ["nonexistent_id", "invalid_inn"])
@pytest.mark.asyncio
async def test_create_receipt_counterparty_validation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    scenario: str,
) -> None:
    payload = _receipt_payload(fn=None, fd=None, fpd=None)
    if scenario == "nonexistent_id":
        payload["counterparty_id"] = "does-not-exist"
        expected = 404
    else:
        payload["counterparty_name"] = "Магазин"
        payload["counterparty_inn"] = "bad-inn"
        expected = 422
    resp = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert resp.status_code == expected


@pytest.mark.asyncio
async def test_create_receipt_with_existing_counterparty_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    cp = Counterparty(
        id=scope_user_id(user_id=test_user.id, public_id="test-cp"),
        user_id=test_user.id,
        name="Тест",
        type="STORE",
    )
    session.add(cp)
    session.commit()

    resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn=None, fd=None, fpd=None, counterparty_id="test-cp"),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["counterparty_id"] == "test-cp"


@pytest.mark.asyncio
async def test_create_receipt_autocreates_counterparty_by_inn(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    payload = _receipt_payload(fn=None, fd=None, fpd=None)
    payload["counterparty_name"] = "Авто Магазин"
    payload["counterparty_inn"] = "1234567890"

    resp = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    cp_id = resp.json()["counterparty_id"]
    assert cp_id is not None
    cp = session.exec(
        select(Counterparty).where(
            Counterparty.id == scope_user_id(user_id=test_user.id, public_id=cp_id)
        )
    ).first()
    assert cp is not None and cp.inn == "1234567890"


@pytest.mark.asyncio
async def test_create_receipt_with_already_linked_document_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    payload = _receipt_payload(fn="1111111111", fd="111111", fpd="1111111111")
    payload["document_id"] = doc_id
    first = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert first.status_code == 201

    payload2 = _receipt_payload(fn="2222222222", fd="222222", fpd="2222222222")
    payload2["document_id"] = doc_id
    second = await client.post("/api/v1/receipts", json=payload2, headers=auth_headers)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_receipt_integrity_error_returns_409_and_rolls_back_document_claim(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    payload = _receipt_payload(fn="7777777777", fd="777777", fpd="7777777777")
    payload["document_id"] = doc_id

    def raise_integrity_error(**_: object) -> None:
        raise IntegrityError("insert receipt", {}, Exception("unique violation"))

    monkeypatch.setattr(receipts_router, "create_receipt", raise_integrity_error)

    resp = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)

    assert resp.status_code == 409
    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == DocumentStatus.PENDING


@pytest.mark.asyncio
async def test_create_receipt_rejects_bank_statement_document(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_doc(client, auth_headers, doc_type="BANK_STATEMENT")
    payload = _receipt_payload(fn="3333333333", fd="333333", fpd="3333333333")
    payload["document_id"] = doc_id

    resp = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_receipt_rejects_processed_document(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    linked_payload = _receipt_payload(fn="4444444444", fd="444444", fpd="4444444444")
    linked_payload["document_id"] = doc_id
    first = await client.post("/api/v1/receipts", json=linked_payload, headers=auth_headers)
    assert first.status_code == 201

    receipt_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="5555555555", fd="555555", fpd="5555555555"),
        headers=auth_headers,
    )
    assert receipt_resp.status_code == 201

    resp = await client.put(
        f"/api/v1/receipts/{receipt_resp.json()['id']}",
        json={"document_id": doc_id},
        headers=auth_headers,
    )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_receipt_integrity_error_returns_409_and_rolls_back_document_claim(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="8888888888", fd="888888", fpd="8888888888"),
        headers=auth_headers,
    )
    assert receipt_resp.status_code == 201

    def raise_integrity_error(**_: object) -> None:
        raise IntegrityError("update receipt", {}, Exception("unique violation"))

    monkeypatch.setattr(receipts_router, "update_receipt", raise_integrity_error)

    resp = await client.put(
        f"/api/v1/receipts/{receipt_resp.json()['id']}",
        json={"document_id": doc_id},
        headers=auth_headers,
    )

    assert resp.status_code == 409
    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == DocumentStatus.PENDING


@pytest.mark.asyncio
async def test_update_receipt_links_and_unlinks_document(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn=None, fd=None, fpd=None),
        headers=auth_headers,
    )
    assert receipt_resp.status_code == 201
    receipt_id = receipt_resp.json()["id"]

    # Link document
    link_resp = await client.put(
        f"/api/v1/receipts/{receipt_id}",
        json={"document_id": doc_id},
        headers=auth_headers,
    )
    assert link_resp.status_code == 200
    assert link_resp.json()["document_id"] == doc_id

    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == "PROCESSED"

    # Unlink document
    unlink_resp = await client.put(
        f"/api/v1/receipts/{receipt_id}",
        json={"document_id": None},
        headers=auth_headers,
    )
    assert unlink_resp.status_code == 200
    assert unlink_resp.json()["document_id"] is None

    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == "PENDING"


@pytest.mark.asyncio
async def test_delete_receipt_resets_linked_document_to_pending(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    payload = _receipt_payload(fn="6666666666", fd="666666", fpd="6666666666")
    payload["document_id"] = doc_id
    receipt_resp = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
    assert receipt_resp.status_code == 201

    delete_resp = await client.delete(
        f"/api/v1/receipts/{receipt_resp.json()['id']}",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 204

    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == DocumentStatus.PENDING


@pytest.mark.asyncio
async def test_update_receipt_rejects_foreign_document(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    foreign_doc_id = await _create_doc(client, second_auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn=None, fd=None, fpd=None),
        headers=auth_headers,
    )
    receipt_id = receipt_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/receipts/{receipt_id}",
        json={"document_id": foreign_doc_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_receipt_rejects_document_linked_to_another_receipt(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_doc(client, auth_headers)

    receipt1 = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="3333333333", fd="333333", fpd="3333333333"),
        headers=auth_headers,
    )
    receipt1_id = receipt1.json()["id"]

    # Link doc to first receipt
    await client.put(
        f"/api/v1/receipts/{receipt1_id}",
        json={"document_id": doc_id},
        headers=auth_headers,
    )

    receipt2 = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn="4444444444", fd="444444", fpd="4444444444"),
        headers=auth_headers,
    )
    receipt2_id = receipt2.json()["id"]

    # Try to link same doc to second receipt
    resp = await client.put(
        f"/api/v1/receipts/{receipt2_id}",
        json={"document_id": doc_id},
        headers=auth_headers,
    )
    assert resp.status_code == 409


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


@pytest.mark.asyncio
async def test_list_receipts_ordered_by_paid_at_desc(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    dates = ["2024-01-10T10:00:00", "2024-03-20T10:00:00", "2024-02-15T10:00:00"]
    for i, date in enumerate(dates):
        payload = _receipt_payload(fn=f"999{i:07d}", fd=f"9{i:05d}", fpd=f"999{i:07d}")
        payload["paid_at"] = date
        r = await client.post("/api/v1/receipts", json=payload, headers=auth_headers)
        assert r.status_code == 201

    resp = await client.get("/api/v1/receipts", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    paid_dates = [item["paid_at"] for item in items]
    assert paid_dates == sorted(paid_dates, reverse=True)


@pytest.mark.asyncio
async def test_update_receipt_stores_scoped_counterparty_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    """Regression: PUT /receipts/{id} must store scoped counterparty_id, not public one."""
    cp = Counterparty(
        id=scope_user_id(user_id=test_user.id, public_id="fix-cp"),
        user_id=test_user.id,
        name="Fix CP",
        type="STORE",
    )
    session.add(cp)
    session.commit()

    receipt_resp = await client.post(
        "/api/v1/receipts",
        json=_receipt_payload(fn=None, fd=None, fpd=None),
        headers=auth_headers,
    )
    assert receipt_resp.status_code == 201
    receipt_id = receipt_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/receipts/{receipt_id}",
        json={"counterparty_id": "fix-cp"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["counterparty_id"] == "fix-cp"

    session.expire_all()
    r = session.get(Receipt, UUID(receipt_id))
    assert r is not None
    assert r.counterparty_id == scope_user_id(user_id=test_user.id, public_id="fix-cp")
