from uuid import UUID

from sqlalchemy import desc
from sqlmodel import Session, select

from app.models.document import Document


def get_document_by_hash(*, session: Session, file_hash: str) -> Document | None:
    return session.exec(select(Document).where(Document.file_hash == file_hash)).first()


def get_document_by_id(
    *,
    session: Session,
    document_id: UUID,
    user_id: UUID,
) -> Document | None:
    return session.exec(
        select(Document).where(Document.id == document_id).where(Document.user_id == user_id)
    ).first()


def get_documents_for_user(
    *,
    session: Session,
    user_id: UUID,
    type_filter: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Document]:
    query = select(Document).where(Document.user_id == user_id)
    if type_filter is not None:
        query = query.where(Document.type == type_filter)
    if status_filter is not None:
        query = query.where(Document.status == status_filter)
    query = query.order_by(desc(Document.uploaded_at)).offset(skip).limit(limit)  # type: ignore[arg-type]
    return list(session.exec(query).all())


def create_document(
    *,
    session: Session,
    user_id: UUID,
    type: str,
    url: str,
    name: str,
    status: str,
    file_hash: str,
    email_source: str | None = None,
) -> Document:
    document = Document(
        user_id=user_id,
        type=type,
        url=url,
        name=name,
        status=status,
        file_hash=file_hash,
        email_source=email_source,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def update_document_status(*, session: Session, document: Document, status: str) -> Document:
    document.status = status
    session.add(document)
    session.commit()
    session.refresh(document)
    return document
