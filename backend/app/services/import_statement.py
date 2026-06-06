from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.constants import BalanceSource, DocumentStatus, DocumentType, ImportStatus
from app.db.accounts import get_account_by_id
from app.db.balances import has_any_balance, upsert_balance
from app.db.classifier_rules import list_rules_for_user
from app.db.documents import claim_document_for_processing, get_document_by_id
from app.db.expense_types import get_expense_type_by_id
from app.db.transactions import create_transaction, find_transaction_by_dedup_key
from app.schemas.bank_statement import (
    BankStatementCreate,
    ConflictItem,
    ImportReport,
    ImportSummary,
)
from app.services.audit import audit_conflict
from app.services.balance_chain import verify_balance_chain
from app.services.classifier import apply_rules

if TYPE_CHECKING:
    from uuid import UUID

    from sqlmodel import Session

    from app.models.user import User


def import_bank_statement(
    *,
    session: Session,
    statement: BankStatementCreate,
    current_user: User,
) -> ImportReport:
    account = get_account_by_id(
        session=session,
        account_id=statement.account_id,
        user_id=current_user.id,
    )
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not found or access denied.",
        )
    document = get_document_by_id(
        session=session,
        document_id=statement.document_id,
        user_id=current_user.id,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    if document.type != DocumentType.BANK_STATEMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type must be BANK_STATEMENT.",
        )
    if document.status != DocumentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )
    if not claim_document_for_processing(session=session, document=document):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already processed.",
        )

    is_initial_import = not has_any_balance(session=session, account_id=statement.account_id)

    active_rules = [
        r for r in list_rules_for_user(session=session, user_id=current_user.id) if r.is_active
    ]

    imported_ids: list[UUID] = []
    skipped_count = 0
    conflicts: list[ConflictItem] = []

    for tx_in in statement.transactions:
        et = get_expense_type_by_id(
            session=session,
            expense_type_id=tx_in.expense_type_id,
            user_id=current_user.id,
        )
        if et is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense type '{tx_in.expense_type_id}' not found.",
            )

        existing, used_fallback = find_transaction_by_dedup_key(
            session=session,
            account_id=statement.account_id,
            occurred_at=tx_in.occurred_at,
            balance_after=tx_in.balance_after,
            amount=tx_in.amount,
        )

        if existing is None:
            new_tx = create_transaction(
                session=session,
                account_id=statement.account_id,
                occurred_at=tx_in.occurred_at,
                processed_at=tx_in.processed_at,
                auth_code=tx_in.auth_code,
                amount=tx_in.amount,
                type=tx_in.type,
                bank_category=tx_in.bank_category,
                expense_type_id=et.id,
                description=tx_in.description,
                balance_after=tx_in.balance_after,
                import_status=ImportStatus.IMPORTED,
                document_id=statement.document_id,
            )
            matched_et_id = apply_rules(active_rules, new_tx)
            if matched_et_id is not None:
                new_tx.expense_type_id = matched_et_id
                session.add(new_tx)
            session.flush()
            imported_ids.append(new_tx.id)

        elif existing.amount == tx_in.amount:
            skipped_count += 1

        else:
            existing.import_status = ImportStatus.CONFLICT
            session.add(existing)
            audit_conflict(
                session=session,
                transaction_id=existing.id,
                existing_data={
                    "amount": str(existing.amount),
                    "occurred_at": str(existing.occurred_at),
                },
                incoming_data={"amount": str(tx_in.amount), "occurred_at": str(tx_in.occurred_at)},
                user_id=current_user.id,
            )
            conflicts.append(
                ConflictItem(
                    transaction_id=existing.id,
                    occurred_at=existing.occurred_at,
                    existing_amount=existing.amount,
                    incoming_amount=tx_in.amount,
                )
            )

    balance_check = verify_balance_chain(
        session=session,
        account_id=statement.account_id,
        period_start=statement.statement_start,
        period_end=statement.statement_end,
        opening_balance=statement.opening_balance,
        expected_closing=statement.closing_balance,
    )

    if statement.opening_balance is not None:
        upsert_balance(
            session=session,
            account_id=statement.account_id,
            amount=statement.opening_balance,
            recorded_at=statement.statement_start,
            source=BalanceSource.OPENING,
            document_id=statement.document_id,
        )
    if statement.closing_balance is not None:
        upsert_balance(
            session=session,
            account_id=statement.account_id,
            amount=statement.closing_balance,
            recorded_at=statement.statement_end,
            source=BalanceSource.CLOSING,
            document_id=statement.document_id,
        )

    session.commit()

    return ImportReport(
        document_id=statement.document_id,
        account_id=statement.account_id,
        period={
            "start": statement.statement_start.date().isoformat(),
            "end": statement.statement_end.date().isoformat(),
        },
        summary=ImportSummary(
            imported_count=len(imported_ids),
            duplicate_count=skipped_count,
            conflict_count=len(conflicts),
        ),
        balance_check=balance_check,
        conflicts=conflicts,
        imported_transaction_ids=imported_ids,
        is_initial_import=is_initial_import,
        opening_balance_missing=statement.opening_balance is None,
    )
