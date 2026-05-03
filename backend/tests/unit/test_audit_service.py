from uuid import uuid4

from sqlmodel import Session, select

from app.constants import AuditAction, AuditEntityType, ChangedBy
from app.models.audit_log import AuditLog
from app.services.audit import audit_create, audit_delete, audit_update


def _first_log(session: Session, entity_id: object) -> AuditLog:
    result = session.exec(
        select(AuditLog).where(AuditLog.entity_id == entity_id)  # type: ignore[arg-type]
    ).first()
    assert result is not None
    return result


def test_audit_create(session: Session) -> None:
    eid = uuid4()
    audit_create(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=eid,
        changed_by=ChangedBy.USER,
        after={"amount": "100.00"},
    )
    session.commit()

    log = _first_log(session, eid)
    assert log.action == AuditAction.CREATE
    assert log.entity_type == AuditEntityType.TRANSACTION
    assert log.changed_by == ChangedBy.USER
    assert "100.00" in log.diff


def test_audit_update(session: Session) -> None:
    eid = uuid4()
    audit_update(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=eid,
        changed_by=ChangedBy.USER,
        before={"amount": "50.00"},
        after={"amount": "75.00"},
    )
    session.commit()

    log = _first_log(session, eid)
    assert log.action == AuditAction.UPDATE
    assert "50.00" in log.diff
    assert "75.00" in log.diff


def test_audit_delete(session: Session) -> None:
    eid = uuid4()
    audit_delete(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=eid,
        changed_by=ChangedBy.USER,
        before={"amount": "200.00"},
    )
    session.commit()

    log = _first_log(session, eid)
    assert log.action == AuditAction.DELETE
    assert "200.00" in log.diff
