from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.db.accounts import (
    create_account,
    delete_account,
    get_account_by_id,
    get_accounts_for_user,
    has_balances_for_account,
    update_account,
)
from app.db.balances import upsert_balance
from app.db.counterparties import get_or_create_counterparty, list_counterparties
from app.db.exchange_rates import create_exchange_rate, get_latest_rates
from app.db.expense_types import (
    create_expense_type,
    delete_expense_type,
    get_expense_type_by_id,
    list_expense_types,
    update_expense_type,
)
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.account import (
    AccountBalanceInit,
    AccountCreate,
    AccountRead,
    AccountUpdate,
)
from app.schemas.counterparty import CounterpartyCreate, CounterpartyRead
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateRead
from app.schemas.expense_type import ExpenseTypeCreate, ExpenseTypeRead, ExpenseTypeUpdate

router = APIRouter(tags=["references"])


# ── Accounts ────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=list[AccountRead])
def list_accounts_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AccountRead]:
    accounts = get_accounts_for_user(session=session, user_id=current_user.id)
    result = []
    for acc in accounts:
        read = AccountRead.model_validate(acc)
        read.has_balances = has_balances_for_account(session=session, account_id=acc.id)
        result.append(read)
    return result


@router.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account_endpoint(
    data: AccountCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccountRead:
    account = create_account(session=session, user_id=current_user.id, data=data)
    read = AccountRead.model_validate(account)
    read.has_balances = False
    return read


@router.put("/accounts/{account_id}", response_model=AccountRead)
def update_account_endpoint(
    account_id: UUID,
    data: AccountUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccountRead:
    account = get_account_by_id(
        session=session, account_id=account_id, user_id=current_user.id
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    account = update_account(session=session, account=account, data=data)
    read = AccountRead.model_validate(account)
    read.has_balances = has_balances_for_account(session=session, account_id=account.id)
    return read


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account_endpoint(
    account_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    account = get_account_by_id(
        session=session, account_id=account_id, user_id=current_user.id
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    delete_account(session=session, account=account)


@router.post("/accounts/{account_id}/initialize-balance", response_model=dict[str, str])
def initialize_balance_endpoint(
    account_id: UUID,
    data: AccountBalanceInit,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    account = get_account_by_id(
        session=session, account_id=account_id, user_id=current_user.id
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not found.")

    balance = upsert_balance(
        session=session,
        account_id=account_id,
        amount=data.amount,
        recorded_at=data.recorded_at,
        source=data.source,
    )
    result = {
        "id": str(balance.id),
        "account_id": str(balance.account_id),
        "amount": str(balance.amount),
        "recorded_at": balance.recorded_at.isoformat(),
        "source": balance.source,
    }
    session.commit()
    return result


# ── Expense Types ────────────────────────────────────────────────────────────

@router.get("/expense-types", response_model=list[ExpenseTypeRead])
def list_expense_types_endpoint(
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> list[ExpenseTypeRead]:
    return [ExpenseTypeRead.model_validate(et) for et in list_expense_types(session=session)]


@router.post("/expense-types", response_model=ExpenseTypeRead, status_code=status.HTTP_201_CREATED)
def create_expense_type_endpoint(
    data: ExpenseTypeCreate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> ExpenseTypeRead:
    et = create_expense_type(session=session, data=data)
    return ExpenseTypeRead.model_validate(et)


@router.put("/expense-types/{expense_type_id}", response_model=ExpenseTypeRead)
def update_expense_type_endpoint(
    expense_type_id: str,
    data: ExpenseTypeUpdate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> ExpenseTypeRead:
    et = get_expense_type_by_id(session=session, expense_type_id=expense_type_id)
    if et is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense type not found.")
    et = update_expense_type(session=session, expense_type=et, data=data)
    return ExpenseTypeRead.model_validate(et)


@router.delete("/expense-types/{expense_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_type_endpoint(
    expense_type_id: str,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> None:
    et = get_expense_type_by_id(session=session, expense_type_id=expense_type_id)
    if et is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense type not found.")
    delete_expense_type(session=session, expense_type=et)


# ── Counterparties ───────────────────────────────────────────────────────────

@router.get("/counterparties", response_model=list[CounterpartyRead])
def list_counterparties_endpoint(
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> list[CounterpartyRead]:
    return [CounterpartyRead.model_validate(c) for c in list_counterparties(session=session)]


@router.post("/counterparties", response_model=CounterpartyRead, status_code=status.HTTP_201_CREATED)
def create_counterparty_endpoint(
    data: CounterpartyCreate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> CounterpartyRead:
    cp = get_or_create_counterparty(
        session=session, name=data.name, type=data.type
    )
    session.commit()
    return CounterpartyRead.model_validate(cp)


# ── Exchange Rates ───────────────────────────────────────────────────────────

@router.post("/exchange-rates", response_model=ExchangeRateRead, status_code=status.HTTP_201_CREATED)
def create_exchange_rate_endpoint(
    data: ExchangeRateCreate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> ExchangeRateRead:
    rate = create_exchange_rate(session=session, data=data)
    return ExchangeRateRead.model_validate(rate)


@router.get("/exchange-rates/latest", response_model=list[ExchangeRateRead])
def get_latest_rates_endpoint(
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> list[ExchangeRateRead]:
    return [ExchangeRateRead.model_validate(r) for r in get_latest_rates(session=session)]
