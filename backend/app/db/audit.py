import json
from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from app.constants import DEFAULT_AUDIT_LOG_LIMIT
from app.models.audit_log import AuditLog
from app.utils.dt import utcnow


def write_audit_log_entry(
    *,
    session: Session,
    entity_type: str,
    entity_id: UUID,
    action: str,
    changed_by: str,
    user_id: UUID | None = None,
    diff_before: dict[str, Any] | None = None,
    diff_after: dict[str, Any] | None = None,
) -> AuditLog:
    diff_payload: dict[str, Any] = {}
    if diff_before is not None:
        diff_payload["before"] = diff_before
    if diff_after is not None:
        diff_payload["after"] = diff_after

    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by=changed_by,
        changed_at=utcnow(),
        user_id=user_id,
        diff=json.dumps(diff_payload, default=str) if diff_payload else None,
    )
    session.add(entry)
    return entry


def list_audit_log_entries(
    *,
    session: Session,
    user_id: UUID,
    entity_type: str | None = None,
    skip: int = 0,
    limit: int = DEFAULT_AUDIT_LOG_LIMIT,
) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.user_id == user_id)
    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
    query = query.order_by(col(AuditLog.changed_at).desc()).offset(skip).limit(limit)
    return list(session.exec(query).all())
