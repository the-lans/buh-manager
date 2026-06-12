from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.constants import RECEIPT_MAX_AGE_DAYS, ApiKeyScope, AuditEntityType, ChangedBy, DocumentStatus, DocumentType
from app.database import get_session
from app.db.counterparties import get_counterparty_by_id, get_or_create_counterparty
from app.db.documents import claim_document_for_processing, get_document_by_id
from app.db.receipts import (
    create_receipt,
    delete_receipt,
    get_linked_transaction_ids,
    get_receipt_by_document_id,
    get_receipt_by_fiscal,
    get_receipt_by_id,
    get_receipt_items,
    get_receipt_linked_transaction,
    get_receipts_for_user,
    update_receipt,
)
from app.dependencies.auth import get_current_user, require_scope
from app.models.document import Document
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
from app.utils.ids import unscope_user_id

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
    user_id = current_user.id
    # Fiscal deduplication (only when all three fields are present)
    if data.fn and data.fd and data.fpd:
        existing = get_receipt_by_fiscal(
            session=session,
            fn=data.fn,
            fd=data.fd,
            fpd=data.fpd,
            user_id=user_id,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Receipt already exists.", "receipt_id": str(existing.id)},
            )

    resolved_counterparty_id = _resolve_counterparty(
        session=session,
        data=data,
        user_id=user_id,
    )

    if data.document_id is not None:
        doc = get_document_by_id(
            session=session,
            document_id=data.document_id,
            user_id=user_id,
        )
        doc = get_or_404(doc, "Document not found.")
        _ensure_receipt_document_linkable(doc)
        if (
            get_receipt_by_document_id(
                session=session,
                document_id=data.document_id,
                user_id=user_id,
            )
            is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is already linked to another receipt.",
            )
        _claim_receipt_document_pending(doc, session=session)
    else:
        doc = None

    try:
        receipt = create_receipt(
            session=session,
            data=data,
            counterparty_id=resolved_counterparty_id,
            user_id=user_id,
        )
    except IntegrityError as exc:
        _raise_receipt_integrity_error(session=session, exc=exc, data=data, user_id=user_id)

    audit_create(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=receipt.id,
        changed_by=ChangedBy.AGENT,
        user_id=user_id,
        after={"receipt_id": str(receipt.id), "total_amount": str(receipt.total_amount)},
    )
    _commit_receipt_document_change(session=session)

    items = get_receipt_items(session=session, receipt_id=receipt.id)
    return _build_receipt_read(receipt, items)


@router.get(
    "",
    response_model=list[ReceiptListItem],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_RECEIPTS))],
)
def list_receipts(
    pagination: PaginationParams = Depends(),
    document_id: UUID | None = Query(default=None),
    unmatched: bool = Query(default=False),
    max_age_days: int | None = Query(default=None, ge=0, le=RECEIPT_MAX_AGE_DAYS),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ReceiptListItem]:
    receipts = get_receipts_for_user(
        session=session,
        user_id=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
        document_id=document_id,
        unmatched=unmatched,
        max_age_days=max_age_days,
    )
    receipt_to_tx = get_linked_transaction_ids(
        session=session,
        receipt_ids=[r.id for r in receipts],
        user_id=current_user.id,
    )
    return [
        ReceiptListItem(
            id=r.id,
            paid_at=r.paid_at,
            total_amount=r.total_amount,
            counterparty_id=unscope_user_id(r.counterparty_id),
            document_id=r.document_id,
            transaction_id=receipt_to_tx.get(r.id),
        )
        for r in receipts
    ]


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
    user_id = current_user.id
    receipt = get_receipt_by_id(session=session, receipt_id=receipt_id, user_id=current_user.id)
    receipt = get_or_404(receipt, "Receipt not found.")

    before = {"total_amount": str(receipt.total_amount), "paid_at": str(receipt.paid_at)}
    old_doc_id = receipt.document_id

    update_counterparty = "counterparty_id" in data.model_fields_set
    resolved_counterparty_id: str | None = None
    if update_counterparty and data.counterparty_id is not None:
        cp = get_counterparty_by_id(
            session=session,
            counterparty_id=data.counterparty_id,
            user_id=user_id,
        )
        if cp is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Counterparty not found.",
            )
        resolved_counterparty_id = cp.id

    new_fn = data.fn if data.fn is not None else receipt.fn
    new_fd = data.fd if data.fd is not None else receipt.fd
    new_fpd = data.fpd if data.fpd is not None else receipt.fpd
    if new_fn and new_fd and new_fpd:
        existing = get_receipt_by_fiscal(
            session=session,
            fn=new_fn,
            fd=new_fd,
            fpd=new_fpd,
            user_id=user_id,
            exclude_receipt_id=receipt.id,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Receipt already exists.", "receipt_id": str(existing.id)},
            )

    new_doc = None
    if (
        "document_id" in data.model_fields_set
        and data.document_id is not None
        and data.document_id != old_doc_id
    ):
        new_doc = get_document_by_id(
            session=session,
            document_id=data.document_id,
            user_id=user_id,
        )
        if new_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )
        _ensure_receipt_document_linkable(new_doc)
        if (
            get_receipt_by_document_id(
                session=session,
                document_id=data.document_id,
                user_id=user_id,
                exclude_receipt_id=receipt.id,
            )
            is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is already linked to another receipt.",
            )
        _claim_receipt_document_pending(new_doc, session=session)

    try:
        receipt = update_receipt(
            session=session,
            receipt=receipt,
            data=data,
            counterparty_id=resolved_counterparty_id,
            update_counterparty=update_counterparty,
        )
    except IntegrityError as exc:
        _raise_receipt_integrity_error(
            session=session,
            exc=exc,
            data=data,
            user_id=user_id,
            exclude_receipt_id=receipt.id,
        )
    after = {"total_amount": str(receipt.total_amount), "paid_at": str(receipt.paid_at)}

    if "document_id" in data.model_fields_set and data.document_id != old_doc_id:
        if old_doc_id is not None:
            old_doc = get_document_by_id(session=session, document_id=old_doc_id, user_id=user_id)
            if old_doc is not None:
                old_doc.status = DocumentStatus.PENDING
                session.add(old_doc)
        if new_doc is not None:
            new_doc.status = DocumentStatus.PROCESSED
            session.add(new_doc)

    audit_update(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=receipt.id,
        changed_by=ChangedBy.USER,
        user_id=user_id,
        before=before,
        after=after,
    )
    _commit_receipt_document_change(session=session)

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

    linked_tx = get_receipt_linked_transaction(
        session=session,
        receipt_id=receipt.id,
        user_id=current_user.id,
    )
    if linked_tx is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receipt is linked to a transaction and cannot be deleted.",
        )

    before = {"receipt_id": str(receipt.id)}
    linked_doc = None
    if receipt.document_id is not None:
        linked_doc = get_document_by_id(
            session=session,
            document_id=receipt.document_id,
            user_id=current_user.id,
        )
    audit_delete(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=receipt.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before=before,
    )
    delete_receipt(session=session, receipt=receipt)
    if linked_doc is not None:
        linked_doc.status = DocumentStatus.PENDING
        session.add(linked_doc)
    session.commit()


def _commit_receipt_document_change(*, session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        _raise_document_link_conflict(session=session, exc=exc)


def _raise_document_link_conflict(*, session: Session, exc: IntegrityError) -> NoReturn:
    session.rollback()
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Document is already linked to another receipt.",
    ) from exc


def _raise_receipt_integrity_error(
    *,
    session: Session,
    exc: IntegrityError,
    data: ReceiptCreate | ReceiptUpdate,
    user_id: UUID,
    exclude_receipt_id: UUID | None = None,
) -> NoReturn:
    session.rollback()
    if data.fn and data.fd and data.fpd:
        existing = get_receipt_by_fiscal(
            session=session,
            fn=data.fn,
            fd=data.fd,
            fpd=data.fpd,
            user_id=user_id,
            exclude_receipt_id=exclude_receipt_id,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Receipt already exists.", "receipt_id": str(existing.id)},
            ) from exc
    _raise_document_link_conflict(session=session, exc=exc)


def _ensure_receipt_document_linkable(document: Document) -> None:
    if document.type != DocumentType.RECEIPT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type must be RECEIPT.",
        )
    if document.status != DocumentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )


def _claim_receipt_document_pending(document: Document, *, session: Session) -> None:
    if not claim_document_for_processing(session=session, document=document):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )


def _resolve_counterparty(*, session: Session, data: ReceiptCreate, user_id: UUID) -> str | None:
    """Return the counterparty id to use for the receipt.

    Priority:
    1. counterparty_id provided → validate it exists, raise 404 if not.
    2. counterparty_id absent, inn + name provided → find-or-create by INN.
    3. Neither → None.
    """
    if data.counterparty_id is not None:
        counterparty = get_counterparty_by_id(
            session=session,
            counterparty_id=data.counterparty_id,
            user_id=user_id,
        )
        if counterparty is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Counterparty not found.",
            )
        return counterparty.id

    if data.counterparty_inn and data.counterparty_name:
        cp = get_or_create_counterparty(
            session=session,
            user_id=user_id,
            name=data.counterparty_name,
            inn=data.counterparty_inn,
        )
        return cp.id

    return None


def _build_receipt_read(receipt: Receipt, items: list[ReceiptItem]) -> ReceiptRead:
    return ReceiptRead(
        id=receipt.id,
        document_id=receipt.document_id,
        paid_at=receipt.paid_at,
        total_amount=receipt.total_amount,
        counterparty_id=receipt.counterparty_id,
        fn=receipt.fn,
        fd=receipt.fd,
        fpd=receipt.fpd,
        items=[ReceiptItemRead.model_validate(item) for item in items],
    )
