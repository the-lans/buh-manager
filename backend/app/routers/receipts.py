import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.constants import ApiKeyScope, AuditEntityType, ChangedBy, DocumentStatus
from app.database import get_session
from app.db.counterparties import get_or_create_counterparty
from app.db.documents import get_document_by_id, update_document_status
from app.db.receipts import (
    create_receipt,
    delete_receipt,
    get_receipt_by_fiscal,
    get_receipt_by_id,
    get_receipt_items,
    get_receipts_for_user,
    update_receipt,
)
from app.dependencies.auth import get_current_user, require_scope
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.models.user import User
from app.schemas.common import PaginationParams
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptItemRead,
    ReceiptListItem,
    ReceiptRead,
    ReceiptUpdate,
)
from app.services.audit import audit_create, audit_delete, audit_update
from app.utils.http import get_or_404

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post(
    "",
    response_model=ReceiptRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_RECEIPTS))],
)
def create_receipt_endpoint(
    data: ReceiptCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptRead:
    # Fiscal deduplication (only when all three fields are present)
    if data.fn and data.fd and data.fpd:
        existing = get_receipt_by_fiscal(
            session=session,
            fn=data.fn,
            fd=data.fd,
            fpd=data.fpd,
            user_id=current_user.id,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Receipt already exists.", "receipt_id": str(existing.id)},
            )

    doc = None
    if data.document_id is not None:
        doc = get_document_by_id(
            session=session, document_id=data.document_id, user_id=current_user.id
        )
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

    counterparty_id: str | None = None
    if data.counterparty_name:
        cp = get_or_create_counterparty(session=session, name=data.counterparty_name)
        counterparty_id = cp.id

    receipt = create_receipt(
        session=session,
        data=data,
        counterparty_id=counterparty_id,
        user_id=current_user.id,
    )

    if doc is not None:
        update_document_status(session=session, document=doc, status=DocumentStatus.PROCESSED)

    audit_create(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=receipt.id,
        changed_by=ChangedBy.AGENT,
        after={"receipt_id": str(receipt.id), "total_amount": str(receipt.total_amount)},
    )
    session.commit()

    items = get_receipt_items(session=session, receipt_id=receipt.id)
    return _build_receipt_read(receipt, items)


@router.get(
    "",
    response_model=list[ReceiptListItem],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_RECEIPTS))],
)
def list_receipts(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ReceiptListItem]:
    receipts = get_receipts_for_user(
        session=session,
        user_id=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return [ReceiptListItem.model_validate(r) for r in receipts]


@router.get(
    "/{receipt_id}",
    response_model=ReceiptRead,
    dependencies=[Depends(require_scope(ApiKeyScope.READ_RECEIPTS))],
)
def get_receipt(
    receipt_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptRead:
    receipt = get_receipt_by_id(session=session, receipt_id=receipt_id, user_id=current_user.id)
    receipt = get_or_404(receipt, "Receipt not found.")
    items = get_receipt_items(session=session, receipt_id=receipt.id)
    return _build_receipt_read(receipt, items)


@router.put(
    "/{receipt_id}",
    response_model=ReceiptRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_RECEIPTS))],
)
def update_receipt_endpoint(
    receipt_id: UUID,
    data: ReceiptUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptRead:
    receipt = get_receipt_by_id(session=session, receipt_id=receipt_id, user_id=current_user.id)
    receipt = get_or_404(receipt, "Receipt not found.")

    before = {"total_amount": str(receipt.total_amount), "paid_at": str(receipt.paid_at)}

    counterparty_id: str | None = None
    if data.counterparty_name:
        cp = get_or_create_counterparty(session=session, name=data.counterparty_name)
        counterparty_id = cp.id

    receipt = update_receipt(
        session=session, receipt=receipt, data=data, counterparty_id=counterparty_id
    )
    after = {"total_amount": str(receipt.total_amount), "paid_at": str(receipt.paid_at)}

    audit_update(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=receipt.id,
        changed_by=ChangedBy.USER,
        before=before,
        after=after,
    )
    session.commit()

    items = get_receipt_items(session=session, receipt_id=receipt.id)
    return _build_receipt_read(receipt, items)


@router.delete(
    "/{receipt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_RECEIPTS))],
)
def delete_receipt_endpoint(
    receipt_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    receipt = get_receipt_by_id(session=session, receipt_id=receipt_id, user_id=current_user.id)
    receipt = get_or_404(receipt, "Receipt not found.")

    before = {"receipt_id": str(receipt.id)}
    audit_delete(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=receipt.id,
        changed_by=ChangedBy.USER,
        before=before,
    )
    delete_receipt(session=session, receipt=receipt)
    session.commit()


def _build_receipt_read(receipt: Receipt, items: list[ReceiptItem]) -> ReceiptRead:
    item_reads = []
    for item in items:
        tags = None
        if item.tags:
            try:
                tags = json.loads(item.tags)
            except ValueError:
                tags = None
        item_reads.append(
            ReceiptItemRead(
                id=item.id,
                code=item.code,
                name=item.name,
                unit=item.unit,
                quantity=item.quantity,
                price=item.price,
                amount=item.amount,
                tags=tags,
            )
        )
    return ReceiptRead(
        id=receipt.id,
        document_id=receipt.document_id,
        paid_at=receipt.paid_at,
        total_amount=receipt.total_amount,
        counterparty_id=receipt.counterparty_id,
        fn=receipt.fn,
        fd=receipt.fd,
        fpd=receipt.fpd,
        items=item_reads,
    )
