from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.constants import ApiKeyScope, AuditEntityType, ChangedBy
from app.database import get_session
from app.db.accounts import get_account_by_id
from app.db.classifier_rules import list_rules_for_user
from app.db.expense_types import get_expense_type_by_id
from app.db.transactions import (
    create_transaction,
    delete_transaction,
    get_transaction_by_id,
    get_transactions_for_user,
    update_transaction,
)
from app.dependencies.auth import get_current_user, require_scope
from app.models.user import User
from app.schemas.common import PaginationParams
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilters,
    TransactionListItem,
    TransactionRead,
    TransactionUpdate,
)
from app.services.audit import audit_create, audit_delete, audit_update
from app.services.classifier import apply_rules
from app.utils.http import get_or_404

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get(
    "",
    response_model=list[TransactionListItem],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_TRANSACTIONS))],
)
def list_transactions(
    filters: TransactionFilters = Depends(),
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[TransactionListItem]:
    txs = get_transactions_for_user(
        session=session,
        user_id=current_user.id,
        filters=filters,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return [TransactionListItem.model_validate(tx) for tx in txs]


@router.post(
    "",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_TRANSACTIONS))],
)
def create_transaction_endpoint(
    data: TransactionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionRead:
    account = get_account_by_id(
        session=session,
        account_id=data.account_id,
        user_id=current_user.id,
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    et = get_or_404(
        get_expense_type_by_id(
            session=session,
            expense_type_id=data.expense_type_id,
            user_id=current_user.id,
        ),
        "Expense type not found.",
    )

    tx = create_transaction(
        session=session,
        account_id=data.account_id,
        occurred_at=data.occurred_at,
        processed_at=data.processed_at,
        auth_code=data.auth_code,
        amount=data.amount,
        type=data.type,
        bank_category=data.bank_category,
        expense_type_id=et.id,
        description=data.description,
        balance_after=data.balance_after,
    )
    if data.apply_rules:
        rules = list_rules_for_user(session=session, user_id=current_user.id)
        matched_et_id = apply_rules([r for r in rules if r.is_active], tx)
        if matched_et_id is not None:
            tx.expense_type_id = matched_et_id
            session.add(tx)
    audit_create(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        after={"amount": str(data.amount), "occurred_at": str(data.occurred_at)},
    )
    session.commit()
    session.refresh(tx)
    return TransactionRead.model_validate(tx)


@router.put(
    "/{transaction_id}",
    response_model=TransactionRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_TRANSACTIONS))],
)
def update_transaction_endpoint(
    transaction_id: UUID,
    data: TransactionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionRead:
    tx = get_transaction_by_id(
        session=session, transaction_id=transaction_id, user_id=current_user.id
    )
    tx = get_or_404(tx, "Transaction not found.")
    if "expense_type_id" in data.model_fields_set and data.expense_type_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="expense_type_id cannot be null.",
        )
    if data.expense_type_id is not None:
        et = get_or_404(
            get_expense_type_by_id(
                session=session,
                expense_type_id=data.expense_type_id,
                user_id=current_user.id,
            ),
            "Expense type not found.",
        )
        data = data.model_copy(update={"expense_type_id": et.id})

    before = {"amount": str(tx.amount), "occurred_at": str(tx.occurred_at)}
    tx = update_transaction(session=session, transaction=tx, data=data)
    if data.apply_rules:
        rules = list_rules_for_user(session=session, user_id=current_user.id)
        matched_et_id = apply_rules([r for r in rules if r.is_active], tx)
        if matched_et_id is not None:
            tx.expense_type_id = matched_et_id
            session.add(tx)
    after = {"amount": str(tx.amount), "occurred_at": str(tx.occurred_at)}

    audit_update(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before=before,
        after=after,
    )
    session.commit()
    return TransactionRead.model_validate(tx)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_TRANSACTIONS))],
)
def delete_transaction_endpoint(
    transaction_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    tx = get_transaction_by_id(
        session=session, transaction_id=transaction_id, user_id=current_user.id
    )
    tx = get_or_404(tx, "Transaction not found.")

    audit_delete(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before={"amount": str(tx.amount), "occurred_at": str(tx.occurred_at)},
    )
    delete_transaction(session=session, transaction=tx)
    session.commit()
