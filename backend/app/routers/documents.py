import io
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlmodel import Session

from app.constants import ApiKeyScope, DocumentStatus
from app.database import get_session
from app.db.documents import (
    create_document,
    get_document_by_id,
    get_documents_for_user,
)
from app.dependencies.auth import get_current_user, require_scope
from app.models.user import User
from app.schemas.common import PaginationParams
from app.schemas.document import DocumentListItem, DocumentRead
from app.services.deduplication import check_document_duplicate, compute_file_hash
from app.utils.http import get_or_404
from storage import get_storage_provider
from storage.base import StorageProvider

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_DOCUMENTS))],
)
async def upload_document(
    file: UploadFile,
    doc_type: str = Query(default="BANK_STATEMENT"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
) -> DocumentRead:
    content = await file.read()
    file_hash = compute_file_hash(content)

    duplicate = check_document_duplicate(session=session, file_hash=file_hash)
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Document already exists.", "document_id": str(duplicate.id)},
        )

    file_id = str(uuid4())
    new_file = UploadFile(
        filename=file.filename,
        file=io.BytesIO(content),
        headers=file.headers,
    )
    url = await storage.upload_file(file=new_file, file_id=file_id)

    document = create_document(
        session=session,
        user_id=current_user.id,
        type=doc_type,
        url=url,
        name=file.filename or file_id,
        status=DocumentStatus.PENDING,
        file_hash=file_hash,
    )
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
