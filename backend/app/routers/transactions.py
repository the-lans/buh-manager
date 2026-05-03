from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.constants import AuditEntityType, ChangedBy
from app.database import get_session
from app.db.accounts import get_account_by_id
from app.db.counterparties import get_or_create_counterparty
from app.db.transactions import (
    create_transaction,
    delete_transaction,
    get_transaction_by_id,
    get_transactions_for_user,
    update_transaction,
)
from app.dependencies.auth import get_current_user
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

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionListItem])
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


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not found.")

    counterparty_id: str | None = None
    if data.counterparty_name:
        cp = get_or_create_counterparty(session=session, name=data.counterparty_name)
        counterparty_id = cp.id

    tx = create_transaction(
        session=session,
        account_id=data.account_id,
        occurred_at=data.occurred_at,
        processed_at=data.processed_at,
        auth_code=data.auth_code,
        amount=data.amount,
        type=data.type,
        bank_category=data.bank_category,
        counterparty_id=counterparty_id,
        expense_type_id=data.expense_type_id,
        description=data.description,
        balance_after=data.balance_after,
    )
    session.flush()
    audit_create(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        after={"amount": str(data.amount), "occurred_at": str(data.occurred_at)},
    )
    session.commit()
    session.refresh(tx)
    return TransactionRead.model_validate(tx)



@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction_endpoint(
    transaction_id: UUID,
    data: TransactionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionRead:
    tx = get_transaction_by_id(
        session=session, transaction_id=transaction_id, user_id=current_user.id
    )
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    before = {"amount": str(tx.amount), "occurred_at": str(tx.occurred_at)}
    tx = update_transaction(session=session, transaction=tx, data=data)
    after = {"amount": str(tx.amount), "occurred_at": str(tx.occurred_at)}

    audit_update(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        before=before,
        after=after,
    )
    session.commit()
    return TransactionRead.model_validate(tx)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction_endpoint(
    transaction_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    tx = get_transaction_by_id(
        session=session, transaction_id=transaction_id, user_id=current_user.id
    )
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    audit_delete(
        session=session,
        entity_type=AuditEntityType.TRANSACTION,
        entity_id=tx.id,
        changed_by=ChangedBy.USER,
        before={"amount": str(tx.amount), "occurred_at": str(tx.occurred_at)},
    )
    delete_transaction(session=session, transaction=tx)
