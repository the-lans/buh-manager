from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.account import Account


def _stmt_payload(
    account_id: str,
    document_id: str,
    txs: list[dict],
    opening: float | None = 1000.0,
    closing: float | None = None,
) -> dict:
    return {
        "document_id": document_id,
        "account_id": account_id,
        "statement_start": "2024-01-01T00:00:00",
        "statement_end": "2024-01-31T23:59:59",
        "opening_balance": opening,
        "closing_balance": closing,
        "transactions": txs,
    }


def _tx(occurred: str, amount: float, balance_after: float | None = None) -> dict:
    d: dict = {"occurred_at": occurred, "amount": amount, "type": "DEBIT"}
    if balance_after is not None:
        d["balance_after"] = balance_after
    return d


async def _create_doc(client: AsyncClient, headers: dict[str, str]) -> str:
    import io

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": (f"stmt_{uuid4()}.pdf", io.BytesIO(uuid4().bytes), "application/pdf")},
        params={"doc_type": "BANK_STATEMENT"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_import_clean(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    payload = _stmt_payload(
        str(test_account.id),
        doc_id,
        [_tx("2024-01-05T10:00:00", -100.0, 900.0)],
        opening=1000.0,
        closing=900.0,
    )
    resp = await client.post("/api/v1/bank-statements", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["imported_count"] == 1
    assert data["summary"]["duplicate_count"] == 0
    assert data["is_initial_import"] is True


@pytest.mark.asyncio
async def test_import_duplicates_skipped(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    payload = _stmt_payload(
        str(test_account.id),
        doc_id,
        [_tx("2024-01-05T10:00:00", -100.0, 900.0)],
        opening=1000.0,
    )
    await client.post("/api/v1/bank-statements", json=payload, headers=auth_headers)

    doc_id2 = await _create_doc(client, auth_headers)
    payload["document_id"] = doc_id2
    resp = await client.post("/api/v1/bank-statements", json=payload, headers=auth_headers)
    data = resp.json()
    assert data["summary"]["duplicate_count"] == 1
    assert data["summary"]["imported_count"] == 0


@pytest.mark.asyncio
async def test_import_conflict_detected(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    doc1 = await _create_doc(client, auth_headers)
    await client.post(
        "/api/v1/bank-statements",
        json=_stmt_payload(
            str(test_account.id),
            doc1,
            [_tx("2024-01-05T10:00:00", -100.0, 900.0)],
        ),
        headers=auth_headers,
    )

    doc2 = await _create_doc(client, auth_headers)
    resp = await client.post(
        "/api/v1/bank-statements",
        json=_stmt_payload(
            str(test_account.id),
            doc2,
            [_tx("2024-01-05T10:00:30", -150.0, 900.0)],  # same balance_after, different amount
        ),
        headers=auth_headers,
    )
    data = resp.json()
    assert data["summary"]["conflict_count"] == 1


@pytest.mark.asyncio
async def test_import_no_balance_after(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    payload = _stmt_payload(
        str(test_account.id),
        doc_id,
        [_tx("2024-01-05T10:00:00", -100.0, None)],  # No balance_after (TBank style)
        opening=None,
    )
    resp = await client.post("/api/v1/bank-statements", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance_check"]["is_available"] is False
    assert data["opening_balance_missing"] is True


@pytest.mark.asyncio
async def test_import_wrong_account_returns_403(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    doc_id = await _create_doc(client, auth_headers)
    payload = _stmt_payload(str(uuid4()), doc_id, [])
    resp = await client.post("/api/v1/bank-statements", json=payload, headers=auth_headers)
    assert resp.status_code == 403
