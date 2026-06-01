from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.constants import (
    ApiKeyScope,
    AuditEntityType,
    ChangedBy,
    ConflictResolutionAction,
    ImportStatus,
    ReconciledStatus,
)
from app.database import get_session
from app.db.receipts import get_receipt_by_id, get_receipt_linked_transaction
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
from app.utils.http import get_or_404

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
    tx = get_or_404(tx, "Transaction not found.")

    if tx.reconciled_status == ReconciledStatus.MATCHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction is already matched.",
        )

    receipt = get_receipt_by_id(
        session=session,
        receipt_id=data.receipt_id,
        user_id=current_user.id,
    )
    receipt = get_or_404(receipt, "Receipt not found.")
    linked_tx = get_receipt_linked_transaction(
        session=session,
        receipt_id=receipt.id,
        user_id=current_user.id,
    )
    if linked_tx is not None and linked_tx.id != tx.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receipt is already matched to another transaction.",
        )

    update_transaction_receipt_link(
        session=session,
        transaction=tx,
        receipt_id=receipt.id,
        reconciled_status=ReconciledStatus.MATCHED,
    )
    audit_match(
        session=session,
        transaction_id=tx.id,
        receipt_id=receipt.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
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
    tx = get_or_404(tx, "Transaction not found.")

    before_status = tx.reconciled_status
    tx.reconciled_status = ReconciledStatus.IGNORED_BY_USER
    tx.receipt_id = None
    session.add(tx)
    audit_update(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
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
    tx = get_or_404(tx, "Transaction not found.")
    if tx.import_status != ImportStatus.CONFLICT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction has no unresolved import conflict.",
        )

    before = {"amount": str(tx.amount), "import_status": str(tx.import_status)}
    if data.action == ConflictResolutionAction.UPDATE_FROM_NEW:
        assert data.incoming_amount is not None
        tx.amount = data.incoming_amount
    tx.import_status = ImportStatus.IMPORTED
    session.add(tx)
    after = {"amount": str(tx.amount), "import_status": str(ImportStatus.IMPORTED)}

    audit_update(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before=before,
        after=after,
    )
    session.commit()
    return {"status": "resolved", "action": data.action}
