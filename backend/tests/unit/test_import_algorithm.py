from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.constants import DocumentStatus, DocumentType
from app.models.account import Account
from app.models.document import Document
from app.models.user import User
from app.schemas.bank_statement import BankStatementCreate, BankStatementTransactionIn
from app.services.import_statement import import_bank_statement
from app.utils.dt import utcnow


def _make_statement(
    account_id: object,
    document_id: object,
    txs: list[BankStatementTransactionIn],
    opening: Decimal | None = None,
    closing: Decimal | None = None,
) -> BankStatementCreate:
    return BankStatementCreate(
        document_id=document_id,  # type: ignore[arg-type]
        account_id=account_id,  # type: ignore[arg-type]
        statement_start=datetime(2024, 1, 1),
        statement_end=datetime(2024, 1, 31),
        opening_balance=opening,
        closing_balance=closing,
        transactions=txs,
    )


def _tx(
    occurred_at: datetime,
    amount: Decimal,
    expense_type_id: str,
    balance_after: Decimal | None = None,
) -> BankStatementTransactionIn:
    return BankStatementTransactionIn(
        occurred_at=occurred_at,
        amount=amount,
        type="DEBIT",
        balance_after=balance_after,
        expense_type_id=expense_type_id,
    )


def _create_document(session: Session, user_id: object) -> Document:
    doc = Document(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        type=DocumentType.BANK_STATEMENT,
        url="/media/test.pdf",
        name="test.pdf",
        status=DocumentStatus.PENDING,
        file_hash=str(uuid4()),
        uploaded_at=utcnow(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


# ── (a) All new → IMPORTED ───────────────────────────────────────────────────


def test_import_all_new(session: Session, test_user: User, test_account: Account, test_expense_type_id: str) -> None:
    doc = _create_document(session, test_user.id)
    txs = [
        _tx(datetime(2024, 1, 5), Decimal("-100"), test_expense_type_id, Decimal("900")),
        _tx(datetime(2024, 1, 6), Decimal("-200"), test_expense_type_id, Decimal("700")),
    ]
    stmt = _make_statement(test_account.id, doc.id, txs, Decimal("1000"), Decimal("700"))
    report = import_bank_statement(session=session, statement=stmt, current_user=test_user)

    assert report.summary.imported_count == 2
    assert report.summary.duplicate_count == 0
    assert report.summary.conflict_count == 0
    assert len(report.imported_transaction_ids) == 2


# ── (b) Exact duplicate → DUPLICATE_SKIPPED ──────────────────────────────────


def test_import_duplicate_skipped(session: Session, test_user: User, test_account: Account, test_expense_type_id: str) -> None:
    doc = _create_document(session, test_user.id)
    txs = [_tx(datetime(2024, 1, 5), Decimal("-100"), test_expense_type_id, Decimal("900"))]
    stmt = _make_statement(test_account.id, doc.id, txs)

    import_bank_statement(session=session, statement=stmt, current_user=test_user)
    doc2 = _create_document(session, test_user.id)
    stmt2 = _make_statement(test_account.id, doc2.id, txs)
    report = import_bank_statement(session=session, statement=stmt2, current_user=test_user)

    assert report.summary.duplicate_count == 1
    assert report.summary.imported_count == 0


# ── (c) Same key + different amount → CONFLICT ───────────────────────────────


def test_import_conflict_detected(session: Session, test_user: User, test_account: Account, test_expense_type_id: str) -> None:
    doc = _create_document(session, test_user.id)
    occurred = datetime(2024, 1, 5)

    stmt1 = _make_statement(
        test_account.id, doc.id, [_tx(occurred, Decimal("-100"), test_expense_type_id, Decimal("900"))]
    )
    import_bank_statement(session=session, statement=stmt1, current_user=test_user)

    doc2 = _create_document(session, test_user.id)
    stmt2 = _make_statement(
        test_account.id, doc2.id, [_tx(occurred, Decimal("-150"), test_expense_type_id, Decimal("900"))]
    )
    report = import_bank_statement(session=session, statement=stmt2, current_user=test_user)

    assert report.summary.conflict_count == 1
    assert report.conflicts[0].existing_amount == Decimal("-100")
    assert report.conflicts[0].incoming_amount == Decimal("-150")


# ── (d) Mixed batch ───────────────────────────────────────────────────────────


def test_import_mixed_batch(session: Session, test_user: User, test_account: Account, test_expense_type_id: str) -> None:
    doc = _create_document(session, test_user.id)
    occurred_dup = datetime(2024, 1, 5)
    occurred_new = datetime(2024, 1, 10)

    stmt1 = _make_statement(
        test_account.id,
        doc.id,
        [_tx(occurred_dup, Decimal("-100"), test_expense_type_id, Decimal("900"))],
    )
    import_bank_statement(session=session, statement=stmt1, current_user=test_user)

    doc2 = _create_document(session, test_user.id)
    stmt2 = _make_statement(
        test_account.id,
        doc2.id,
        [
            _tx(occurred_dup, Decimal("-100"), test_expense_type_id, Decimal("900")),  # duplicate
            _tx(occurred_new, Decimal("-200"), test_expense_type_id, Decimal("700")),  # new
        ],
    )
    report = import_bank_statement(session=session, statement=stmt2, current_user=test_user)

    assert report.summary.imported_count == 1
    assert report.summary.duplicate_count == 1
    assert report.summary.conflict_count == 0


# ── (e) Empty transaction list ────────────────────────────────────────────────


def test_import_empty_transactions(
    session: Session, test_user: User, test_account: Account
) -> None:
    doc = _create_document(session, test_user.id)
    stmt = _make_statement(test_account.id, doc.id, [])
    report = import_bank_statement(session=session, statement=stmt, current_user=test_user)

    assert report.summary.imported_count == 0
    assert report.summary.duplicate_count == 0


# ── (f) Account not owned by user → 403 ──────────────────────────────────────


def test_import_wrong_account_raises_403(session: Session, test_account: Account) -> None:
    other_user = User(
        id=uuid4(),
        email="other@example.com",
        is_active=True,
        created_at=utcnow(),
    )
    session.add(other_user)
    session.commit()

    doc = _create_document(session, other_user.id)
    stmt = _make_statement(test_account.id, doc.id, [])

    with pytest.raises(HTTPException) as exc_info:
        import_bank_statement(session=session, statement=stmt, current_user=other_user)
    assert exc_info.value.status_code == 403
