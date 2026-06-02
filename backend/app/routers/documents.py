import hashlib
import io
import mimetypes
from contextlib import suppress
from pathlib import Path
from tempfile import SpooledTemporaryFile
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.constants import (
    MAX_UPLOAD_FILE_SIZE,
    MEDIA_PATH,
    UPLOAD_READ_CHUNK_SIZE,
    ApiKeyScope,
    AuditEntityType,
    ChangedBy,
    DocumentStatus,
    DocumentType,
)
from app.database import get_session
from app.db.accounts import get_account_by_id
from app.db.balances import link_balances_to_document
from app.db.documents import (
    claim_document_for_processing,
    create_document,
    get_document_by_id,
    get_documents_for_user,
    update_document,
)
from app.db.receipts import get_receipt_by_id
from app.db.transactions import link_transactions_to_document
from app.dependencies.auth import get_current_user, require_scope
from app.models.user import User
from app.schemas.common import PaginationParams
from app.schemas.document import (
    DocumentListItem,
    DocumentRead,
    DocumentUpdate,
    LinkReceiptRequest,
    LinkResult,
    LinkStatementRequest,
)
from app.services.audit import audit_update
from app.services.deduplication import check_document_duplicate
from app.utils.http import get_or_404
from storage import get_storage_provider
from storage.base import StorageProvider

router = APIRouter(prefix="/documents", tags=["documents"])


async def _read_with_size_limit(*, file: UploadFile, max_size: int) -> bytes:
    content, _ = await _read_with_size_limit_and_hash(file=file, max_size=max_size)
    return content


async def _read_with_size_limit_and_hash(*, file: UploadFile, max_size: int) -> tuple[bytes, str]:
    total_size = 0
    hasher = hashlib.sha256()
    with SpooledTemporaryFile(max_size=max_size) as buffer:
        while True:
            chunk = await file.read(UPLOAD_READ_CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=(
                        f"File size exceeds maximum allowed size of {max_size // (1024 * 1024)} MB."
                    ),
                )
            hasher.update(chunk)
            buffer.write(chunk)
        buffer.seek(0)
        return buffer.read(), hasher.hexdigest()


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_DOCUMENTS))],
)
async def upload_document(
    file: UploadFile,
    doc_type: DocumentType = Query(default=DocumentType.BANK_STATEMENT),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
) -> DocumentRead:
    content, file_hash = await _read_with_size_limit_and_hash(
        file=file,
        max_size=MAX_UPLOAD_FILE_SIZE,
    )

    duplicate = check_document_duplicate(
        session=session,
        file_hash=file_hash,
        user_id=current_user.id,
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Document already exists.", "document_id": str(duplicate.id)},
        )

    file_id = str(uuid4())
    file_bytes = io.BytesIO(content)
    new_file = UploadFile(
        filename=file.filename,
        file=file_bytes,
        headers=file.headers,
    )
    try:
        url = await storage.upload_file(file=new_file, file_id=file_id)

        try:
            document = create_document(
                session=session,
                user_id=current_user.id,
                type=doc_type,
                url=url,
                name=file.filename or file_id,
                status=DocumentStatus.PENDING,
                file_hash=file_hash,
            )
            session.commit()
            session.refresh(document)
        except IntegrityError as exc:
            session.rollback()
            with suppress(RuntimeError):
                await storage.delete_file(doc_url=url)
            duplicate = check_document_duplicate(
                session=session,
                file_hash=file_hash,
                user_id=current_user.id,
            )
            detail: dict[str, str] = {"message": "Document already exists."}
            if duplicate is not None:
                detail["document_id"] = str(duplicate.id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc
    finally:
        file_bytes.close()
    return DocumentRead.model_validate(document)


@router.get(
    "",
    response_model=list[DocumentListItem],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_DOCUMENTS))],
)
def list_documents(
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[DocumentListItem]:
    docs = get_documents_for_user(
        session=session,
        user_id=current_user.id,
        type_filter=type,
        status_filter=status,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return [DocumentListItem.model_validate(d) for d in docs]


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    dependencies=[Depends(require_scope(ApiKeyScope.READ_DOCUMENTS))],
)
def get_document(
    document_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    doc = get_document_by_id(session=session, document_id=document_id, user_id=current_user.id)
    doc = get_or_404(doc, "Document not found.")
    return DocumentRead.model_validate(doc)


@router.put(
    "/{document_id}",
    response_model=DocumentRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_DOCUMENTS))],
)
def update_document_endpoint(
    document_id: UUID,
    data: DocumentUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    doc = get_document_by_id(session=session, document_id=document_id, user_id=current_user.id)
    doc = get_or_404(doc, "Document not found.")
    doc = update_document(session=session, document=doc, data=data)
    session.commit()
    return DocumentRead.model_validate(doc)


@router.get(
    "/{document_id}/download",
    response_model=None,
    dependencies=[Depends(require_scope(ApiKeyScope.READ_DOCUMENTS))],
)
def download_document(
    document_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
) -> FileResponse | JSONResponse:
    doc = get_document_by_id(session=session, document_id=document_id, user_id=current_user.id)
    doc = get_or_404(doc, "Document not found.")

    inline = request.query_params.get("inline", "false").lower() == "true"

    if _is_local_path(doc.url):
        local_path = Path(MEDIA_PATH) / Path(doc.url).name
        if not local_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk.",
            )
        media_type = mimetypes.guess_type(doc.name)[0] or "application/octet-stream"
        return FileResponse(
            path=str(local_path),
            filename=doc.name,
            media_type=media_type,
        )

    presigned_url = storage.get_download_url(
        doc_url=doc.url,
        filename=doc.name,
        inline=inline,
    )
    return JSONResponse({"url": presigned_url})


@router.post(
    "/{document_id}/link-receipt",
    response_model=LinkResult,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_DOCUMENTS))],
)
def link_document_to_receipt(
    document_id: UUID,
    data: LinkReceiptRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LinkResult:
    doc = get_document_by_id(session=session, document_id=document_id, user_id=current_user.id)
    doc = get_or_404(doc, "Document not found.")

    if doc.type != DocumentType.RECEIPT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type must be RECEIPT.",
        )
    if doc.status != DocumentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )

    receipt = get_receipt_by_id(
        session=session, receipt_id=data.receipt_id, user_id=current_user.id
    )
    receipt = get_or_404(receipt, "Receipt not found.")

    if receipt.document_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receipt already has a linked document.",
        )

    if not claim_document_for_processing(session=session, document=doc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )
    receipt.document_id = document_id
    session.add(receipt)
    session.flush()
    audit_update(
        session=session,
        entity_type=AuditEntityType.RECEIPT,
        entity_id=receipt.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before={"document_id": None},
        after={"document_id": str(document_id)},
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already linked to another receipt.",
        ) from exc

    return LinkResult(
        document_id=document_id,
        status=DocumentStatus.PROCESSED,
        updated_count=1,
    )


@router.post(
    "/{document_id}/link-statement",
    response_model=LinkResult,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_DOCUMENTS))],
)
def link_document_to_statement(
    document_id: UUID,
    data: LinkStatementRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LinkResult:
    doc = get_document_by_id(session=session, document_id=document_id, user_id=current_user.id)
    doc = get_or_404(doc, "Document not found.")

    if doc.type != DocumentType.BANK_STATEMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type must be BANK_STATEMENT.",
        )
    if doc.status != DocumentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )

    account = get_account_by_id(
        session=session, account_id=data.account_id, user_id=current_user.id
    )
    account = get_or_404(account, "Account not found.")

    if not claim_document_for_processing(session=session, document=doc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )
    tx_count = link_transactions_to_document(
        session=session,
        account_id=account.id,
        user_id=current_user.id,
        date_start=data.statement_start,
        date_end=data.statement_end,
        document_id=document_id,
    )
    bal_count = link_balances_to_document(
        session=session,
        account_id=account.id,
        date_start=data.statement_start,
        date_end=data.statement_end,
        document_id=document_id,
    )
    total = tx_count + bal_count

    if total == 0:
        new_status = DocumentStatus.ERROR
        message = "Не найдено транзакций или остатков для привязки."  # noqa: RUF001
    else:
        new_status = DocumentStatus.PROCESSED
        message = None

    doc.status = new_status
    session.add(doc)
    session.flush()
    audit_update(
        session=session,
        entity_type=AuditEntityType.IMPORT,
        entity_id=document_id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before={"document_status": DocumentStatus.PENDING},
        after={
            "document_status": new_status,
            "linked_transactions": tx_count,
            "linked_balances": bal_count,
        },
    )
    session.commit()

    return LinkResult(
        document_id=document_id,
        status=new_status,
        updated_count=total,
        message=message,
    )


@router.post(
    "/{document_id}/reset",
    response_model=DocumentRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_DOCUMENTS))],
)
def reset_document(
    document_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """Reset a document from ERROR status back to PENDING so it can be re-processed."""
    doc = get_document_by_id(session=session, document_id=document_id, user_id=current_user.id)
    doc = get_or_404(doc, "Document not found.")

    if doc.status != DocumentStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only documents with ERROR status can be reset.",
        )

    doc.status = DocumentStatus.PENDING
    session.add(doc)
    session.flush()
    audit_update(
        session=session,
        entity_type=AuditEntityType.IMPORT,
        entity_id=document_id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before={"document_status": DocumentStatus.ERROR},
        after={"document_status": DocumentStatus.PENDING},
    )
    session.commit()
    session.refresh(doc)
    return DocumentRead.model_validate(doc)


def _is_local_path(url: str) -> bool:
    return url.startswith("/")
