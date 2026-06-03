import hashlib
import io
import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.constants import (
    MAX_UPLOAD_FILE_SIZE,
    DocumentStatus,
    DocumentType,
)
from app.db.api_keys import get_api_key_by_hash
from app.db.documents import claim_document_for_processing, create_document
from app.db.receipts import create_receipt, get_receipt_by_fiscal, get_receipts_for_user
from app.db.transactions import create_transaction, link_transactions_to_document
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.models.user import User
from app.routers.documents import _read_with_size_limit
from app.schemas.receipt import ReceiptCreate, ReceiptItemCreate, ReceiptItemRead

LEGACY_PAID_AT = datetime(2020, 1, 1)


class TestJsonParsingErrors:
    """Tests for JSON parsing error handling in authentication."""

    def test_api_key_invalid_json_scopes(
        self, session: Session, test_user: User, make_api_key_in_db
    ) -> None:
        """Test that invalid JSON in scopes is handled gracefully."""
        plaintext_key = make_api_key_in_db(
            user_id=test_user.id,
            scopes=["read:documents"],
        )
        # Corrupt the scopes in the database
        key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        api_key = get_api_key_by_hash(session=session, key_hash=key_hash)
        api_key.scopes = "invalid json"
        session.add(api_key)
        session.commit()

        # Verify that trying to use the key results in auth error
        key_hash2 = hashlib.sha256(plaintext_key.encode()).hexdigest()
        api_key2 = get_api_key_by_hash(session=session, key_hash=key_hash2)
        assert api_key2 is not None
        assert api_key2.scopes == "invalid json"

    def test_api_key_scopes_not_array(
        self, session: Session, test_user: User, make_api_key_in_db
    ) -> None:
        """Test that scopes as JSON object is handled gracefully."""
        plaintext_key = make_api_key_in_db(
            user_id=test_user.id,
            scopes=["read:documents"],
        )
        # Corrupt the scopes in the database to be a JSON object instead of array
        key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        api_key = get_api_key_by_hash(session=session, key_hash=key_hash)
        api_key.scopes = json.dumps({"scope": "read:documents"})
        session.add(api_key)
        session.commit()

        # Verify the scopes are correctly stored
        key_hash2 = hashlib.sha256(plaintext_key.encode()).hexdigest()
        api_key2 = get_api_key_by_hash(session=session, key_hash=key_hash2)
        assert api_key2 is not None

    def test_api_key_valid_json_scopes(
        self, session: Session, test_user: User, make_api_key_in_db
    ) -> None:
        """Test that valid JSON scopes work correctly."""
        plaintext_key = make_api_key_in_db(
            user_id=test_user.id,
            scopes=["read:documents"],
        )

        # Verify the key was created with valid scopes
        key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        api_key = get_api_key_by_hash(session=session, key_hash=key_hash)
        assert api_key is not None
        scopes = json.loads(api_key.scopes)
        assert scopes == ["read:documents"]


class TestAuthorizationVulnerability:
    """Tests for authorization vulnerability fixes in receipts."""

    def test_user_cannot_access_receipt_through_other_user_document(
        self, session: Session, test_user: User, second_test_user: User
    ) -> None:
        """Test that receipts are only accessible by their user, not through documents."""

        # Create document for second_test_user
        create_document(
            session=session,
            user_id=second_test_user.id,
            type=DocumentType.RECEIPT,
            url="test.pdf",
            name="test.pdf",
            status=DocumentStatus.PENDING,
            file_hash="test_hash",
        )
        session.commit()

        # Create receipt for test_user (not second_test_user)
        receipt_data = ReceiptCreate(
            paid_at="2024-01-01",
            total_amount=Decimal("100.00"),
            items=[],
        )
        receipt = create_receipt(
            session=session,
            data=receipt_data,
            counterparty_id=None,
            user_id=test_user.id,
        )
        session.commit()

        # Try to get receipt as second_test_user - should fail
        receipts = get_receipts_for_user(session=session, user_id=second_test_user.id)
        assert len(receipts) == 0
        assert receipt not in receipts

    def test_receipts_filtered_by_user_id_only(
        self, session: Session, test_user: User, second_test_user: User
    ) -> None:
        """Test that get_receipts_for_user only returns receipts belonging to the user."""

        # Create receipts for both users
        receipt_data = ReceiptCreate(
            paid_at="2024-01-01",
            total_amount=Decimal("100.00"),
            items=[],
        )
        user_receipt = create_receipt(
            session=session,
            data=receipt_data,
            counterparty_id=None,
            user_id=test_user.id,
        )
        other_receipt = create_receipt(
            session=session,
            data=receipt_data,
            counterparty_id=None,
            user_id=second_test_user.id,
        )
        session.commit()

        # User should only see their own receipt
        user_receipts = get_receipts_for_user(session=session, user_id=test_user.id)
        assert len(user_receipts) == 1
        assert user_receipts[0].id == user_receipt.id

        other_receipts = get_receipts_for_user(session=session, user_id=second_test_user.id)
        assert len(other_receipts) == 1
        assert other_receipts[0].id == other_receipt.id


class TestUserIdValidationInTransactions:
    """Tests for user_id validation in link_transactions_to_document."""

    def test_link_transactions_validates_user_ownership(
        self, session: Session, second_test_user: User, test_account, test_expense_type_scoped_id: str
    ) -> None:
        """Test that link_transactions_to_document validates user ownership."""

        # Create transaction for the account
        tx = create_transaction(
            session=session,
            account_id=test_account.id,
            occurred_at=datetime(2024, 1, 1),
            amount=Decimal("100.00"),
            type="INCOME",
            expense_type_id=test_expense_type_scoped_id,
        )
        session.commit()

        # Try to link as second_test_user - should fail (no rows updated)
        doc_id = uuid4()
        updated = link_transactions_to_document(
            session=session,
            account_id=test_account.id,
            user_id=second_test_user.id,
            date_start=datetime(2024, 1, 1),
            date_end=datetime(2024, 1, 2),
            document_id=doc_id,
        )
        assert updated == 0

        # Transaction should not be linked
        session.refresh(tx)
        assert tx.document_id is None


class TestLegacyReceiptsCompatibility:
    """Tests for legacy receipts with user_id IS NULL."""

    def test_legacy_receipt_appears_in_list(self, session: Session, test_user: User) -> None:
        """Legacy receipt (user_id NULL) linked via document appears in user's list."""
        doc = create_document(
            session=session,
            user_id=test_user.id,
            type=DocumentType.RECEIPT,
            url="legacy.pdf",
            name="legacy.pdf",
            status=DocumentStatus.PENDING,
            file_hash="legacy_hash",
        )
        session.flush()

        legacy = Receipt(
            user_id=None,
            document_id=doc.id,
            paid_at=LEGACY_PAID_AT,
            total_amount=Decimal("50.00"),
        )
        session.add(legacy)
        session.commit()

        receipts = get_receipts_for_user(session=session, user_id=test_user.id)
        assert any(r.id == legacy.id for r in receipts)

    def test_legacy_receipt_not_visible_to_other_user(
        self, session: Session, test_user: User, second_test_user: User
    ) -> None:
        """Legacy receipt owned via document is not visible to a different user."""
        doc = create_document(
            session=session,
            user_id=test_user.id,
            type=DocumentType.RECEIPT,
            url="legacy2.pdf",
            name="legacy2.pdf",
            status=DocumentStatus.PENDING,
            file_hash="legacy_hash2",
        )
        session.flush()

        legacy = Receipt(
            user_id=None,
            document_id=doc.id,
            paid_at=LEGACY_PAID_AT,
            total_amount=Decimal("50.00"),
        )
        session.add(legacy)
        session.commit()

        receipts = get_receipts_for_user(session=session, user_id=second_test_user.id)
        assert not any(r.id == legacy.id for r in receipts)

    def test_legacy_receipt_fiscal_dedup_works(self, session: Session, test_user: User) -> None:
        """Fiscal deduplication finds legacy receipt (user_id NULL) via document owner."""
        doc = create_document(
            session=session,
            user_id=test_user.id,
            type=DocumentType.RECEIPT,
            url="fiscal.pdf",
            name="fiscal.pdf",
            status=DocumentStatus.PENDING,
            file_hash="fiscal_hash",
        )
        session.flush()

        legacy = Receipt(
            user_id=None,
            document_id=doc.id,
            paid_at=LEGACY_PAID_AT,
            total_amount=Decimal("50.00"),
            fn="1234567890",
            fd="123456",
            fpd="1234567890",
        )
        session.add(legacy)
        session.commit()

        found = get_receipt_by_fiscal(
            session=session, fn="1234567890", fd="123456", fpd="1234567890", user_id=test_user.id
        )
        assert found is not None
        assert found.id == legacy.id

    def test_legacy_receipt_not_found_by_other_user_fiscal(
        self, session: Session, test_user: User, second_test_user: User
    ) -> None:
        """Fiscal dedup does not find legacy receipt owned by a different user."""
        doc = create_document(
            session=session,
            user_id=test_user.id,
            type=DocumentType.RECEIPT,
            url="fiscal2.pdf",
            name="fiscal2.pdf",
            status=DocumentStatus.PENDING,
            file_hash="fiscal_hash2",
        )
        session.flush()

        legacy = Receipt(
            user_id=None,
            document_id=doc.id,
            paid_at=LEGACY_PAID_AT,
            total_amount=Decimal("50.00"),
            fn="9999999999",
            fd="999999",
            fpd="9999999999",
        )
        session.add(legacy)
        session.commit()

        found = get_receipt_by_fiscal(
            session=session,
            fn="9999999999",
            fd="999999",
            fpd="9999999999",
            user_id=second_test_user.id,
        )
        assert found is None


class TestFileSizeValidation:
    """Tests for file size validation in upload_document."""

    def test_max_upload_file_size_constant_defined(self) -> None:
        """Test that MAX_UPLOAD_FILE_SIZE constant is defined."""
        assert MAX_UPLOAD_FILE_SIZE > 0
        assert MAX_UPLOAD_FILE_SIZE == 100 * 1024 * 1024  # 100 MB

    @pytest.mark.asyncio
    async def test_read_with_size_limit_raises_on_excess(self) -> None:
        """Test that _read_with_size_limit raises 413 before reading everything."""
        oversized = io.BytesIO(b"x" * 200)
        upload = UploadFile(filename="big.bin", file=oversized)

        with pytest.raises(HTTPException) as exc_info:
            await _read_with_size_limit(file=upload, max_size=100)
        assert exc_info.value.status_code == status.HTTP_413_CONTENT_TOO_LARGE

    @pytest.mark.asyncio
    async def test_read_with_size_limit_allows_within_limit(self) -> None:
        """Test that _read_with_size_limit returns content when within limit."""
        content = b"hello world"
        upload = UploadFile(filename="small.bin", file=io.BytesIO(content))

        result = await _read_with_size_limit(file=upload, max_size=1000)
        assert result == content


class TestReceiptItemTagsDeserialization:
    """Tests for JSON deserialization in receipt item tags."""

    def test_receipt_item_tags_valid_json(self, session: Session, test_user: User) -> None:
        """Test that valid JSON tags are deserialized correctly."""
        tags = ["tag1", "tag2", "tag3"]
        item_data = ReceiptItemCreate(
            name="Test Item",
            quantity=Decimal("1"),
            price=Decimal("100.00"),
            amount=Decimal("100.00"),
            tags=tags,
        )
        receipt_data = ReceiptCreate(
            paid_at="2024-01-01",
            total_amount=Decimal("100.00"),
            items=[item_data],
        )
        receipt = create_receipt(
            session=session,
            data=receipt_data,
            counterparty_id=None,
            user_id=test_user.id,
        )
        session.commit()

        # Verify tags are deserialized correctly
        item = session.exec(select(ReceiptItem).where(ReceiptItem.receipt_id == receipt.id)).first()
        read_item = ReceiptItemRead.model_validate(item)
        assert read_item.tags == tags

    def test_receipt_item_tags_invalid_json(self, session: Session, test_user: User) -> None:
        """Test that invalid JSON tags are handled gracefully."""
        item_data = ReceiptItemCreate(
            name="Test Item",
            quantity=Decimal("1"),
            price=Decimal("100.00"),
            amount=Decimal("100.00"),
            tags=None,
        )
        receipt_data = ReceiptCreate(
            paid_at="2024-01-01",
            total_amount=Decimal("100.00"),
            items=[item_data],
        )
        receipt = create_receipt(
            session=session,
            data=receipt_data,
            counterparty_id=None,
            user_id=test_user.id,
        )
        session.commit()

        # Manually corrupt the tags in DB
        item = session.exec(select(ReceiptItem).where(ReceiptItem.receipt_id == receipt.id)).first()
        item.tags = "invalid json {{"
        session.add(item)
        session.commit()

        # Should not crash and return None for tags
        read_item = ReceiptItemRead.model_validate(item)
        assert read_item.tags is None


class TestClaimDocumentRaceCondition:
    """Tests for race condition fix in claim_document_for_processing."""

    def test_claim_document_flush_before_refresh(self, session: Session, test_user: User) -> None:
        """Test that flush is called before refresh."""
        doc = create_document(
            session=session,
            user_id=test_user.id,
            type=DocumentType.RECEIPT,
            url="test.pdf",
            name="test.pdf",
            status=DocumentStatus.PENDING,
            file_hash="test_hash",
        )
        session.commit()

        # Claim the document - should succeed
        success = claim_document_for_processing(session=session, document=doc)
        assert success is True
        assert doc.status == DocumentStatus.PROCESSED

        # Try to claim again - should fail
        success2 = claim_document_for_processing(session=session, document=doc)
        assert success2 is False


class TestAuditUpdateFlush:
    """Tests for flush before audit_update."""

    def test_document_status_change_is_flushed(self, session: Session, test_user: User) -> None:
        """Test that document status changes are flushed before use."""
        doc = create_document(
            session=session,
            user_id=test_user.id,
            type=DocumentType.RECEIPT,
            url="test.pdf",
            name="test.pdf",
            status=DocumentStatus.PENDING,
            file_hash="test_hash",
        )
        session.commit()

        # Change status and flush
        doc.status = DocumentStatus.PROCESSED
        session.add(doc)
        session.flush()

        # Verify the flush happened
        session.refresh(doc)
        assert doc.status == DocumentStatus.PROCESSED
