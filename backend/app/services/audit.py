from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.constants import AuditAction, AuditEntityType, ChangedBy
from app.db.audit import write_audit_log_entry
from app.models.audit_log import AuditLog


def audit_create(
    *,
    session: Session,
    entity_type: AuditEntityType,
    entity_id: UUID,
    changed_by: ChangedBy,
    after: dict[str, Any],
) -> AuditLog:
    return write_audit_log_entry(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.CREATE,
        changed_by=changed_by,
        diff_after=after,
    )


def audit_update(
    *,
    session: Session,
    entity_type: AuditEntityType,
    entity_id: UUID,
    changed_by: ChangedBy,
    before: dict[str, Any],
    after: dict[str, Any],
) -> AuditLog:
    return write_audit_log_entry(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.UPDATE,
        changed_by=changed_by,
        diff_before=before,
        diff_after=after,
    )


def audit_delete(
    *,
    session: Session,
    entity_type: AuditEntityType,
    entity_id: UUID,
    changed_by: ChangedBy,
    before: dict[str, Any],
) -> AuditLog:
    return write_audit_log_entry(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.DELETE,
        changed_by=changed_by,
        diff_before=before,
    )


def audit_match(
    *,
    session: Session,
    transaction_id: UUID,
    receipt_id: UUID,
    changed_by: ChangedBy,
) -> AuditLog:
    return write_audit_log_entry(
        session=session,
        entity_type=AuditEntityType.MATCH,
        entity_id=transaction_id,
        action=AuditAction.MATCH,
        changed_by=changed_by,
        diff_after={"receipt_id": str(receipt_id)},
    )


def audit_conflict(
    *,
    session: Session,
    transaction_id: UUID,
    existing_data: dict[str, Any],
    incoming_data: dict[str, Any],
) -> AuditLog:
    return write_audit_log_entry(
        session=session,
        entity_type=AuditEntityType.IMPORT,
        entity_id=transaction_id,
        action=AuditAction.IMPORT_CONFLICT,
        changed_by=ChangedBy.AGENT,
        diff_before=existing_data,
        diff_after=incoming_data,
    )
