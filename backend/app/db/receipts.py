import json
from uuid import UUID

from sqlmodel import Session, select

from app.models.document import Document
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.schemas.receipt import ReceiptCreate, ReceiptItemCreate, ReceiptUpdate


def get_receipt_by_fiscal(
    *,
    session: Session,
    fn: str,
    fd: str,
    fpd: str,
) -> Receipt | None:
    return session.exec(
        select(Receipt)
        .where(Receipt.fn == fn)
        .where(Receipt.fd == fd)
        .where(Receipt.fpd == fpd)
    ).first()


def get_receipt_by_id(
    *,
    session: Session,
    receipt_id: UUID,
    user_id: UUID,
) -> Receipt | None:
    # A receipt is accessible if its document belongs to the user,
    # or if created without a document (agent flow) — check via account path not applicable,
    # so we check document ownership when document_id is set.
    receipt = session.get(Receipt, receipt_id)
    if receipt is None:
        return None
    if receipt.document_id is not None:
        doc = session.get(Document, receipt.document_id)
        if doc is None or doc.user_id != user_id:
            return None
        return receipt
    # Receipt without document: not directly user-scoped by FK, allow access
    # (In a multi-user scenario, receipts without documents should be linked to accounts.
    # For now, we trust the agent flow and allow access.)
    return receipt


def get_receipts_for_user(
    *,
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Receipt]:
    return list(
        session.exec(
            select(Receipt)
            .join(Document, Receipt.document_id == Document.id)  # type: ignore[arg-type]
            .where(Document.user_id == user_id)
            .offset(skip)
            .limit(limit)
        ).all()
    )


def get_unmatched_receipts(*, session: Session, user_id: UUID) -> list[Receipt]:
    # Include receipts linked to the user's documents AND receipts without any document
    # (agent-created receipts that aren't document-scoped).
    return list(
        session.exec(
            select(Receipt)
            .join(Document, Receipt.document_id == Document.id, isouter=True)  # type: ignore[arg-type]
            .where(
                (Receipt.document_id == None)  # noqa: E711
                | (Document.user_id == user_id)
            )
        ).all()
    )


def create_receipt(
    *,
    session: Session,
    data: ReceiptCreate,
    counterparty_id: str | None,
) -> Receipt:
    receipt = Receipt(
        document_id=data.document_id,
        paid_at=data.paid_at,
        total_amount=data.total_amount,
        counterparty_id=counterparty_id,
        fn=data.fn,
        fd=data.fd,
        fpd=data.fpd,
    )
    session.add(receipt)
    session.flush()  # Get receipt.id before creating items

    for item_data in data.items:
        _create_receipt_item(session=session, receipt_id=receipt.id, data=item_data)

    session.commit()
    session.refresh(receipt)
    return receipt


def _create_receipt_item(
    *,
    session: Session,
    receipt_id: UUID,
    data: ReceiptItemCreate,
) -> ReceiptItem:
    item = ReceiptItem(
        receipt_id=receipt_id,
        code=data.code,
        name=data.name,
        unit=data.unit,
        quantity=data.quantity,
        price=data.price,
        amount=data.amount,
        tags=json.dumps(data.tags, ensure_ascii=False) if data.tags else None,
    )
    session.add(item)
    return item


def get_receipt_items(*, session: Session, receipt_id: UUID) -> list[ReceiptItem]:
    return list(
        session.exec(select(ReceiptItem).where(ReceiptItem.receipt_id == receipt_id)).all()
    )


def update_receipt(
    *,
    session: Session,
    receipt: Receipt,
    data: ReceiptUpdate,
    counterparty_id: str | None = None,
) -> Receipt:
    if data.paid_at is not None:
        receipt.paid_at = data.paid_at
    if data.total_amount is not None:
        receipt.total_amount = data.total_amount
    if data.fn is not None:
        receipt.fn = data.fn
    if data.fd is not None:
        receipt.fd = data.fd
    if data.fpd is not None:
        receipt.fpd = data.fpd
    if counterparty_id is not None:
        receipt.counterparty_id = counterparty_id
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    return receipt


def delete_receipt(*, session: Session, receipt: Receipt) -> None:
    items = session.exec(select(ReceiptItem).where(ReceiptItem.receipt_id == receipt.id)).all()
    for item in items:
        session.delete(item)
    session.flush()  # ensure items are removed before receipt to satisfy FK constraint
    session.delete(receipt)
    session.commit()
