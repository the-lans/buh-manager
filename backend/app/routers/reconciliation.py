from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.constants import ApiKeyScope, AuditEntityType, ChangedBy, ImportStatus, ReconciledStatus
from app.database import get_session
from app.db.reconciliation_reports import get_last_report
from app.db.transactions import get_transaction_by_id, update_transaction_receipt_link
from app.dependencies.auth import get_current_user, require_scope
from app.models.user import User
from app.schemas.reconciliation import (
    IgnoreRequest,
    ManualMatchRequest,
    ReconciliationReport,
    ResolveConflictRequest,
)
from app.services.audit import audit_match, audit_update
from app.services.reconciliation import run_reconciliation

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.post(
    "/run",
    response_model=ReconciliationReport,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_RECONCILIATION))],
)
def run_reconciliation_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReconciliationReport:
    return run_reconciliation(session=session, current_user=current_user)


@router.get(
    "/report",
    response_model=ReconciliationReport | None,
    dependencies=[Depends(require_scope(ApiKeyScope.READ_RECONCILIATION))],
)
def get_last_report_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReconciliationReport | None:
    data = get_last_report(session=session, user_id=current_user.id)
    if data is None:
        return None
    return ReconciliationReport.model_validate(data)


@router.post(
    "/match",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_RECONCILIATION))],
)
def manual_match(
    data: ManualMatchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    tx = get_transaction_by_id(
        session=session, transaction_id=data.transaction_id, user_id=current_user.id
    )
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    update_transaction_receipt_link(
        session=session,
        transaction=tx,
        receipt_id=data.receipt_id,
        reconciled_status=ReconciledStatus.MATCHED,
    )
    audit_match(
        session=session,
        transaction_id=tx.id,
        receipt_id=data.receipt_id,
        changed_by=ChangedBy.USER,
    )
    session.commit()
    return {"status": "matched"}


@router.post(
    "/ignore",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_RECONCILIATION))],
)
def ignore_transaction(
    data: IgnoreRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    tx = get_transaction_by_id(
        session=session, transaction_id=data.transaction_id, user_id=current_user.id
    )
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    before_status = tx.reconciled_status
    tx.reconciled_status = ReconciledStatus.IGNORED_BY_USER
    session.add(tx)
    audit_update(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        before={"reconciled_status": before_status},
        after={"reconciled_status": ReconciledStatus.IGNORED_BY_USER},
    )
    session.commit()
    return {"status": "ignored"}


@router.post(
    "/resolve-conflict",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_RECONCILIATION))],
)
def resolve_conflict(
    data: ResolveConflictRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    tx = get_transaction_by_id(
        session=session, transaction_id=data.transaction_id, user_id=current_user.id
    )
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    before = {"amount": str(tx.amount), "import_status": str(tx.import_status)}

    tx.import_status = ImportStatus.IMPORTED
    session.add(tx)
    after = {"import_status": str(ImportStatus.IMPORTED)}

    audit_update(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        before=before,
        after=after,
    )
    session.commit()
    return {"status": "resolved", "action": data.action}
