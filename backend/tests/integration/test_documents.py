import io
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.constants import MEDIA_PATH, DocumentStatus
from app.main import app
from app.models.account import Account
from app.models.balance import Balance
from app.models.document import Document
from app.models.receipt import Receipt
from app.models.transaction import Transaction
from app.routers import documents as documents_router
from storage import get_storage_provider


class RecordingStorageProvider:
    def __init__(self) -> None:
        self.uploaded_url: str | None = None
        self.deleted_url: str | None = None
        self.fail_delete = False

    async def upload_file(self, *, file: object, file_id: str) -> str:  # noqa: ARG002
        self.uploaded_url = f"/media/fake/{file_id}"
        return self.uploaded_url

    async def delete_file(self, *, doc_url: str) -> None:
        if self.fail_delete:
            raise RuntimeError("delete failed")
        self.deleted_url = doc_url

    def get_download_url(
        self,
        *,
        doc_url: str,
        filename: str,  # noqa: ARG002
        inline: bool = False,  # noqa: ARG002
        expires_in: int = 3600,  # noqa: ARG002
    ) -> str:
        return doc_url


def _pdf_bytes(content: str = "fake pdf content") -> bytes:
    return content.encode()


@pytest.mark.asyncio
async def test_upload_new_document(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("statement.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        params={"doc_type": "BANK_STATEMENT"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "statement.pdf"
    assert "id" in data


@pytest.mark.asyncio
async def test_upload_duplicate_document_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    content = _pdf_bytes("unique content for dup test")
    await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("doc.pdf", io.BytesIO(content), "application/pdf")},
    )
    response = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("doc.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 409
    assert "document_id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_integrity_error_returns_409_and_deletes_uploaded_file(
    client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = RecordingStorageProvider()
    app.dependency_overrides[get_storage_provider] = lambda: storage

    def raise_integrity_error(**_: object) -> None:
        raise IntegrityError("insert document", {}, Exception("unique violation"))

    monkeypatch.setattr(documents_router, "create_document", raise_integrity_error)

    response = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("doc.pdf", io.BytesIO(_pdf_bytes("race")), "application/pdf")},
    )

    assert response.status_code == 409
    assert storage.deleted_url == storage.uploaded_url


@pytest.mark.asyncio
async def test_upload_integrity_error_returns_409_when_cleanup_fails(
    client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = RecordingStorageProvider()
    storage.fail_delete = True
    app.dependency_overrides[get_storage_provider] = lambda: storage

    def raise_integrity_error(**_: object) -> None:
        raise IntegrityError("insert document", {}, Exception("unique violation"))

    monkeypatch.setattr(documents_router, "create_document", raise_integrity_error)

    response = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("doc.pdf", io.BytesIO(_pdf_bytes("race-cleanup")), "application/pdf")},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_upload_runtime_error_cleans_up_uploaded_file(
    client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = RecordingStorageProvider()
    app.dependency_overrides[get_storage_provider] = lambda: storage

    def raise_runtime_error(**_: object) -> None:
        raise RuntimeError("db exploded")

    monkeypatch.setattr(documents_router, "create_document", raise_runtime_error)

    with pytest.raises(RuntimeError, match="db exploded"):
        await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("doc.pdf", io.BytesIO(_pdf_bytes("runtime")), "application/pdf")},
        )

    assert storage.deleted_url == storage.uploaded_url


@pytest.mark.asyncio
async def test_two_users_can_upload_same_file(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    """Per-user SHA-256 dedup: different users may upload the same file."""
    content = _pdf_bytes("shared file content for both users")
    r1 = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("shared.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/documents",
        headers=second_auth_headers,
        files={"file": ("shared.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]  # separate documents for each user


@pytest.mark.asyncio
async def test_list_documents_with_type_filter(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("bs.pdf", io.BytesIO(_pdf_bytes("bs1")), "application/pdf")},
        params={"doc_type": "BANK_STATEMENT"},
    )
    await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("rc.pdf", io.BytesIO(_pdf_bytes("rc1")), "application/pdf")},
        params={"doc_type": "RECEIPT"},
    )

    resp = await client.get(
        "/api/v1/documents",
        headers=auth_headers,
        params={"type": "BANK_STATEMENT"},
    )
    assert resp.status_code == 200
    docs = resp.json()
    assert all(d["type"] == "BANK_STATEMENT" for d in docs)


@pytest.mark.asyncio
async def test_get_document_by_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    upload = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("x.pdf", io.BytesIO(_pdf_bytes("get_by_id")), "application/pdf")},
    )
    doc_id = upload.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_get_other_user_document_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    upload = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("private.pdf", io.BytesIO(_pdf_bytes("private")), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=second_auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_document_serves_file(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    content = b"%PDF-1.4 fake pdf"
    upload = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("invoice.pdf", io.BytesIO(content), "application/pdf")},
        params={"doc_type": "RECEIPT"},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]
    doc_url = upload.json()["url"]

    media_dir = Path(MEDIA_PATH)
    media_dir.mkdir(exist_ok=True)
    file_path = media_dir / Path(doc_url).name
    file_path.write_bytes(content)
    try:
        resp = await client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.content == content
    finally:
        file_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_download_nonexistent_document_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get(
        f"/api/v1/documents/{uuid4()}/download",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_other_user_document_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    upload = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("secret.pdf", io.BytesIO(_pdf_bytes("secret")), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}/download", headers=second_auth_headers)
    assert resp.status_code == 404


# ── link-receipt endpoint ──────────────────────────────────────────────────────


def _receipt_payload(total: float = 100.0) -> dict:
    return {
        "paid_at": "2024-03-01T10:00:00",
        "total_amount": total,
        "fn": str(uuid4().int)[:10],
        "fd": str(uuid4().int)[:6],
        "fpd": str(uuid4().int)[:10],
        "items": [{"name": "Тест", "quantity": "1", "price": str(total), "amount": str(total)}],
    }


async def _create_receipt_doc(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": (f"r_{uuid4()}.pdf", io.BytesIO(uuid4().bytes), "application/pdf")},
        params={"doc_type": "RECEIPT"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_stmt_doc(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": (f"s_{uuid4()}.pdf", io.BytesIO(uuid4().bytes), "application/pdf")},
        params={"doc_type": "BANK_STATEMENT"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_link_receipt_to_document_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
) -> None:
    doc_id = await _create_receipt_doc(client, auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts", json=_receipt_payload(), headers=auth_headers
    )
    assert receipt_resp.status_code == 201
    receipt_id = receipt_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-receipt",
        json={"receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == DocumentStatus.PROCESSED
    assert data["updated_count"] == 1

    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == DocumentStatus.PROCESSED

    receipt = session.get(Receipt, UUID(receipt_id))
    assert receipt is not None
    assert str(receipt.document_id) == doc_id


@pytest.mark.asyncio
async def test_link_receipt_wrong_doc_type_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts", json=_receipt_payload(), headers=auth_headers
    )
    receipt_id = receipt_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-receipt",
        json={"receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_link_receipt_already_processed_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_receipt_doc(client, auth_headers)
    r1 = await client.post("/api/v1/receipts", json=_receipt_payload(), headers=auth_headers)
    r2 = await client.post("/api/v1/receipts", json=_receipt_payload(), headers=auth_headers)
    receipt_id1 = r1.json()["id"]
    receipt_id2 = r2.json()["id"]

    # First link succeeds
    await client.post(
        f"/api/v1/documents/{doc_id}/link-receipt",
        json={"receipt_id": receipt_id1},
        headers=auth_headers,
    )
    # Second attempt: document already PROCESSED
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-receipt",
        json={"receipt_id": receipt_id2},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_link_receipt_already_has_document_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc1 = await _create_receipt_doc(client, auth_headers)
    doc2 = await _create_receipt_doc(client, auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts", json=_receipt_payload(), headers=auth_headers
    )
    receipt_id = receipt_resp.json()["id"]

    # Link receipt to doc1
    await client.post(
        f"/api/v1/documents/{doc1}/link-receipt",
        json={"receipt_id": receipt_id},
        headers=auth_headers,
    )
    # Try to link same receipt to doc2 (doc2 is PENDING, but receipt already has doc1)
    resp = await client.post(
        f"/api/v1/documents/{doc2}/link-receipt",
        json={"receipt_id": receipt_id},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_link_receipt_not_found_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_receipt_doc(client, auth_headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-receipt",
        json={"receipt_id": str(uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_link_receipt_other_user_doc_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_receipt_doc(client, auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts", json=_receipt_payload(), headers=second_auth_headers
    )
    receipt_id = receipt_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-receipt",
        json={"receipt_id": receipt_id},
        headers=second_auth_headers,
    )
    assert resp.status_code == 404  # doc belongs to user1, not user2


# ── link-statement endpoint ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_link_statement_to_document_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
) -> None:
    # Import a bank statement to create transactions and balances
    doc_import = await _create_stmt_doc(client, auth_headers)
    stmt_payload = {
        "document_id": doc_import,
        "account_id": str(test_account.id),
        "statement_start": "2024-02-01T00:00:00",
        "statement_end": "2024-02-28T23:59:59",
        "opening_balance": 1000.0,
        "closing_balance": 900.0,
        "transactions": [{"occurred_at": "2024-02-10T12:00:00", "amount": -100.0, "type": "DEBIT", "expense_type_id": test_expense_type_id}],
    }
    import_resp = await client.post(
        "/api/v1/bank-statements", json=stmt_payload, headers=auth_headers
    )
    assert import_resp.status_code == 200

    # Now unlink transactions from their document to simulate PENDING scenario
    for tx in session.exec(
        select(Transaction).where(Transaction.account_id == test_account.id)
    ).all():
        tx.document_id = None
        session.add(tx)
    for bal in session.exec(select(Balance).where(Balance.account_id == test_account.id)).all():
        bal.document_id = None
        session.add(bal)
    session.commit()

    # Upload a new PENDING document
    doc_id = await _create_stmt_doc(client, auth_headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2024-02-01T00:00:00",
            "statement_end": "2024-02-28T23:59:59",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == DocumentStatus.PROCESSED
    assert data["updated_count"] > 0


@pytest.mark.asyncio
async def test_link_statement_no_transactions_sets_error(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2025-01-01T00:00:00",
            "statement_end": "2025-01-31T23:59:59",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == DocumentStatus.ERROR
    assert data["updated_count"] == 0

    # Verify document status in DB
    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == DocumentStatus.ERROR


@pytest.mark.asyncio
async def test_link_statement_wrong_doc_type_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    doc_id = await _create_receipt_doc(client, auth_headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2024-01-01T00:00:00",
            "statement_end": "2024-01-31T23:59:59",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_link_statement_wrong_account_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)

    # Create account for second user
    acc_resp = await client.post(
        "/api/v1/accounts",
        json={"bank": "Other", "account_number": "40817810000000000099"},
        headers=second_auth_headers,
    )
    assert acc_resp.status_code == 201
    other_account_id = acc_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": other_account_id,
            "statement_start": "2024-01-01T00:00:00",
            "statement_end": "2024-01-31T23:59:59",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_link_statement_invalid_date_range_returns_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    doc_id = await _create_stmt_doc(client, auth_headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2024-02-28T00:00:00",
            "statement_end": "2024-02-01T00:00:00",  # end before start
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_link_statement_normalizes_timezone_aware_range(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(test_account.id),
            "occurred_at": "2024-01-31T21:30:00Z",
            "amount": -100.0,
            "type": "EXPENSE",
            "expense_type_id": test_expense_type_id,
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201

    doc_id = await _create_stmt_doc(client, auth_headers)
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2024-02-01T00:00:00+03:00",
            "statement_end": "2024-02-01T23:59:59+03:00",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 1


@pytest.mark.asyncio
async def test_link_document_error_status_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    """A document already in ERROR status cannot be re-processed."""
    doc_id = await _create_stmt_doc(client, auth_headers)

    # Trigger ERROR status by linking with empty range
    await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2030-01-01T00:00:00",
            "statement_end": "2030-01-31T23:59:59",
        },
        headers=auth_headers,
    )

    # Second attempt should fail because status is now ERROR (not PENDING)
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2030-01-01T00:00:00",
            "statement_end": "2030-01-31T23:59:59",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 409


# ── reset endpoint ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_error_document_to_pending(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    session: Session,
) -> None:
    """ERROR document can be reset back to PENDING for retry."""
    doc_id = await _create_stmt_doc(client, auth_headers)

    # Drive document into ERROR
    await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2099-01-01T00:00:00",
            "statement_end": "2099-01-31T23:59:59",
        },
        headers=auth_headers,
    )

    resp = await client.post(f"/api/v1/documents/{doc_id}/reset", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == DocumentStatus.PENDING

    # Verify DB
    session.expire_all()
    doc = session.get(Document, UUID(doc_id))
    assert doc is not None
    assert doc.status == DocumentStatus.PENDING


@pytest.mark.asyncio
async def test_reset_pending_document_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Cannot reset a PENDING document (already in initial state)."""
    doc_id = await _create_stmt_doc(client, auth_headers)
    resp = await client.post(f"/api/v1/documents/{doc_id}/reset", headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_reset_processed_document_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Cannot reset a PROCESSED document (already linked)."""
    doc_id = await _create_receipt_doc(client, auth_headers)
    receipt_resp = await client.post(
        "/api/v1/receipts", json=_receipt_payload(), headers=auth_headers
    )
    receipt_id = receipt_resp.json()["id"]
    await client.post(
        f"/api/v1/documents/{doc_id}/link-receipt",
        json={"receipt_id": receipt_id},
        headers=auth_headers,
    )

    resp = await client.post(f"/api/v1/documents/{doc_id}/reset", headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_reset_after_error_allows_reprocessing(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
) -> None:
    """After reset, link-statement should succeed if transactions exist now."""
    # Import a statement first so transactions exist
    import_doc = await _create_stmt_doc(client, auth_headers)
    stmt_payload = {
        "document_id": import_doc,
        "account_id": str(test_account.id),
        "statement_start": "2024-06-01T00:00:00",
        "statement_end": "2024-06-30T23:59:59",
        "opening_balance": 1000.0,
        "closing_balance": 900.0,
        "transactions": [{"occurred_at": "2024-06-10T10:00:00", "amount": -100.0, "type": "DEBIT", "expense_type_id": test_expense_type_id}],
    }
    await client.post("/api/v1/bank-statements", json=stmt_payload, headers=auth_headers)

    # Unlink transactions
    for tx in session.exec(
        select(Transaction).where(Transaction.account_id == test_account.id)
    ).all():
        tx.document_id = None
        session.add(tx)
    for bal in session.exec(select(Balance).where(Balance.account_id == test_account.id)).all():
        bal.document_id = None
        session.add(bal)
    session.commit()

    # New document in ERROR state (wrong date range initially)
    doc_id = await _create_stmt_doc(client, auth_headers)
    await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2099-01-01T00:00:00",
            "statement_end": "2099-01-31T23:59:59",
        },
        headers=auth_headers,
    )

    # Reset
    await client.post(f"/api/v1/documents/{doc_id}/reset", headers=auth_headers)

    # Retry with correct date range
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/link-statement",
        json={
            "account_id": str(test_account.id),
            "statement_start": "2024-06-01T00:00:00",
            "statement_end": "2024-06-30T23:59:59",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == DocumentStatus.PROCESSED
