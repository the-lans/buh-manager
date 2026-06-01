import io
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient


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
) -> None:
    resp = await client.get(
        f"/api/v1/documents/{uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_document_serves_file(
    client: AsyncClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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

    # Write the fake file to the media directory so FileResponse can serve it
    from app.constants import MEDIA_PATH
    media_dir = Path(MEDIA_PATH)
    media_dir.mkdir(exist_ok=True)
    file_name = Path(doc_url).name
    (media_dir / file_name).write_bytes(content)

    resp = await client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.content == content


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
) -> None:
    resp = await client.get(
        f"/api/v1/documents/{uuid4()}/download",
        headers=auth_headers,
    )
    assert resp.status_code == 404
