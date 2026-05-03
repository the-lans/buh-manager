import hashlib

from sqlmodel import Session

from app.db.documents import get_document_by_hash
from app.models.document import Document


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def check_document_duplicate(*, session: Session, file_hash: str) -> Document | None:
    return get_document_by_hash(session=session, file_hash=file_hash)
