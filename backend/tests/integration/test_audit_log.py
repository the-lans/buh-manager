from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.constants import AuditAction, AuditEntityType, ChangedBy
from app.db.audit import write_audit_log_entry
from app.models.user import User


def _write_entry(
    session: Session,
    user_id: UUID,
    entity_type: str = AuditEntityType.RECEIPT,
    action: str = AuditAction.CREATE,
) -> None:
    write_audit_log_entry(
        session=session,
        entity_type=entity_type,
        entity_id=uuid4(),
        action=action,
        changed_by=ChangedBy.USER,
        user_id=user_id,
        diff_after={"field": "value"},
    )
    session.commit()


@pytest.mark.asyncio
async def test_list_audit_log_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get("/api/v1/audit-log", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_audit_log_returns_entries(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    _write_entry(session, user_id=test_user.id, entity_type=AuditEntityType.RECEIPT)
    _write_entry(session, user_id=test_user.id, entity_type=AuditEntityType.TRANSACTION)

    resp = await client.get("/api/v1/audit-log", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert {"entity_type", "action", "changed_by", "changed_at", "id"} <= set(data[0].keys())


@pytest.mark.asyncio
async def test_list_audit_log_sorted_desc(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    for _ in range(3):
        _write_entry(session, user_id=test_user.id)

    resp = await client.get("/api/v1/audit-log", headers=auth_headers)
    assert resp.status_code == 200
    timestamps = [e["changed_at"] for e in resp.json()]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_list_audit_log_filter_by_entity_type(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    _write_entry(session, user_id=test_user.id, entity_type=AuditEntityType.RECEIPT)
    _write_entry(session, user_id=test_user.id, entity_type=AuditEntityType.RECEIPT)
    _write_entry(session, user_id=test_user.id, entity_type=AuditEntityType.TRANSACTION)

    resp = await client.get(
        "/api/v1/audit-log",
        params={"entity_type": AuditEntityType.RECEIPT},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(e["entity_type"] == AuditEntityType.RECEIPT for e in data)


@pytest.mark.asyncio
async def test_list_audit_log_pagination(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    for _ in range(5):
        _write_entry(session, user_id=test_user.id)

    resp = await client.get("/api/v1/audit-log", params={"limit": 2}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = await client.get(
        "/api/v1/audit-log",
        params={"skip": 2, "limit": 2},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2
    ids_page1 = {e["id"] for e in resp.json()}
    ids_page2 = {e["id"] for e in resp2.json()}
    assert ids_page1.isdisjoint(ids_page2)
