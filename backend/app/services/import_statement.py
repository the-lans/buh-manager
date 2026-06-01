from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session

from app.constants import BalanceSource, ImportStatus
from app.db.accounts import get_account_by_id
from app.db.balances import has_any_balance, upsert_balance
from app.db.counterparties import get_or_create_counterparty
from app.db.transactions import create_transaction, find_transaction_by_dedup_key
from app.models.user import User
from app.schemas.bank_statement import (
    BankStatementCreate,
    ConflictItem,
    ImportReport,
    ImportSummary,
)
from app.services.audit import audit_conflict
from app.services.balance_chain import verify_balance_chain


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

    is_initial_import = not has_any_balance(session=session, account_id=statement.account_id)

    imported_ids: list[UUID] = []
    skipped_count = 0
    conflicts: list[ConflictItem] = []

    for tx_in in statement.transactions:
        counterparty_id: str | None = None
        if tx_in.counterparty_name:
            cp = get_or_create_counterparty(session=session, name=tx_in.counterparty_name)
            counterparty_id = cp.id

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
                counterparty_id=counterparty_id,
                description=tx_in.description,
                balance_after=tx_in.balance_after,
                import_status=ImportStatus.IMPORTED,
                document_id=statement.document_id,
            )
            session.flush()
            imported_ids.append(new_tx.id)

        elif existing.amount == tx_in.amount:
            skipped_count += 1

        else:
            audit_conflict(
                session=session,
                transaction_id=existing.id,
                existing_data={
                    "amount": str(existing.amount),
                    "occurred_at": str(existing.occurred_at),
                },
                incoming_data={"amount": str(tx_in.amount), "occurred_at": str(tx_in.occurred_at)},
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
