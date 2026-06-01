from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.constants import DEFAULT_AUDIT_LOG_LIMIT, ApiKeyScope
from app.database import get_session
from app.db.audit import list_audit_log_entries
from app.dependencies.auth import get_current_user, require_scope
from app.models.user import User
from app.schemas.audit_log import AuditLogRead

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get(
    "",
    response_model=list[AuditLogRead],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_AUDIT_LOG))],
)
def list_audit_log_endpoint(
    entity_type: str | None = None,
    skip: int = 0,
    limit: int = DEFAULT_AUDIT_LOG_LIMIT,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AuditLogRead]:
    entries = list_audit_log_entries(
        session=session,
        user_id=current_user.id,
        entity_type=entity_type,
        skip=skip,
        limit=limit,
    )
    return [AuditLogRead.model_validate(e) for e in entries]
