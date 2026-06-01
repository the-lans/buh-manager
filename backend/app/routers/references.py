from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.constants import ApiKeyScope
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
from app.db.counterparties import (
    delete_counterparty,
    get_counterparty_by_id,
    get_or_create_counterparty,
    list_counterparties,
    update_counterparty,
)
from app.db.exchange_rates import create_exchange_rate, get_latest_rates
from app.db.expense_types import (
    create_expense_type,
    delete_expense_type,
    get_expense_type_by_id,
    list_expense_types,
    update_expense_type,
)
from app.dependencies.auth import get_current_user, require_scope
from app.models.user import User
from app.schemas.account import (
    AccountBalanceInit,
    AccountCreate,
    AccountRead,
    AccountUpdate,
)
from app.schemas.counterparty import CounterpartyCreate, CounterpartyRead, CounterpartyUpdate
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateRead
from app.schemas.expense_type import ExpenseTypeCreate, ExpenseTypeRead, ExpenseTypeUpdate
from app.utils.http import get_or_404

router = APIRouter(tags=["references"])


# ── Accounts ────────────────────────────────────────────────────────────────


@router.get(
    "/accounts",
    response_model=list[AccountRead],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_ACCOUNTS))],
)
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


@router.post(
    "/accounts",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_ACCOUNTS))],
)
def create_account_endpoint(
    data: AccountCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccountRead:
    account = create_account(session=session, user_id=current_user.id, data=data)
    read = AccountRead.model_validate(account)
    read.has_balances = False
    return read


@router.put(
    "/accounts/{account_id}",
    response_model=AccountRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_ACCOUNTS))],
)
def update_account_endpoint(
    account_id: UUID,
    data: AccountUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccountRead:
    account = get_account_by_id(session=session, account_id=account_id, user_id=current_user.id)
    account = get_or_404(account, "Account not found.")
    account = update_account(session=session, account=account, data=data)
    read = AccountRead.model_validate(account)
    read.has_balances = has_balances_for_account(session=session, account_id=account.id)
    return read


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_ACCOUNTS))],
)
def delete_account_endpoint(
    account_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    account = get_account_by_id(session=session, account_id=account_id, user_id=current_user.id)
    account = get_or_404(account, "Account not found.")
    delete_account(session=session, account=account)


@router.post(
    "/accounts/{account_id}/initialize-balance",
    response_model=dict[str, str],
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_ACCOUNTS))],
)
def initialize_balance_endpoint(
    account_id: UUID,
    data: AccountBalanceInit,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    account = get_account_by_id(session=session, account_id=account_id, user_id=current_user.id)
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


@router.get(
    "/expense-types",
    response_model=list[ExpenseTypeRead],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_EXPENSE_TYPES))],
)
def list_expense_types_endpoint(
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> list[ExpenseTypeRead]:
    return [ExpenseTypeRead.model_validate(et) for et in list_expense_types(session=session)]


@router.post(
    "/expense-types",
    response_model=ExpenseTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_EXPENSE_TYPES))],
)
def create_expense_type_endpoint(
    data: ExpenseTypeCreate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> ExpenseTypeRead:
    et = create_expense_type(session=session, data=data)
    return ExpenseTypeRead.model_validate(et)


@router.put(
    "/expense-types/{expense_type_id}",
    response_model=ExpenseTypeRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_EXPENSE_TYPES))],
)
def update_expense_type_endpoint(
    expense_type_id: str,
    data: ExpenseTypeUpdate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> ExpenseTypeRead:
    et = get_expense_type_by_id(session=session, expense_type_id=expense_type_id)
    et = get_or_404(et, "Expense type not found.")
    et = update_expense_type(session=session, expense_type=et, data=data)
    return ExpenseTypeRead.model_validate(et)


@router.delete(
    "/expense-types/{expense_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_EXPENSE_TYPES))],
)
def delete_expense_type_endpoint(
    expense_type_id: str,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> None:
    et = get_expense_type_by_id(session=session, expense_type_id=expense_type_id)
    et = get_or_404(et, "Expense type not found.")
    delete_expense_type(session=session, expense_type=et)


# ── Counterparties ───────────────────────────────────────────────────────────


@router.get(
    "/counterparties",
    response_model=list[CounterpartyRead],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_COUNTERPARTIES))],
)
def list_counterparties_endpoint(
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> list[CounterpartyRead]:
    return [CounterpartyRead.model_validate(c) for c in list_counterparties(session=session)]


@router.post(
    "/counterparties",
    response_model=CounterpartyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_COUNTERPARTIES))],
)
def create_counterparty_endpoint(
    data: CounterpartyCreate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> CounterpartyRead:
    cp = get_or_create_counterparty(
        session=session,
        name=data.name,
        type=data.type,
        inn=data.inn,
        kpp=data.kpp,
    )
    session.commit()
    return CounterpartyRead.model_validate(cp)


@router.put(
    "/counterparties/{counterparty_id}",
    response_model=CounterpartyRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_COUNTERPARTIES))],
)
def update_counterparty_endpoint(
    counterparty_id: str,
    data: CounterpartyUpdate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> CounterpartyRead:
    cp = get_counterparty_by_id(session=session, counterparty_id=counterparty_id)
    cp = get_or_404(cp, "Counterparty not found.")
    cp = update_counterparty(
        session=session,
        counterparty=cp,
        update_data=data.model_dump(exclude_unset=True),
    )
    session.commit()
    return CounterpartyRead.model_validate(cp)


@router.delete(
    "/counterparties/{counterparty_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_COUNTERPARTIES))],
)
def delete_counterparty_endpoint(
    counterparty_id: str,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> None:
    cp = get_counterparty_by_id(session=session, counterparty_id=counterparty_id)
    cp = get_or_404(cp, "Counterparty not found.")
    delete_counterparty(session=session, counterparty=cp)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Контрагент используется в транзакциях или чеках и не может быть удалён.",
        ) from exc


# ── Exchange Rates ───────────────────────────────────────────────────────────


@router.post(
    "/exchange-rates",
    response_model=ExchangeRateRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_EXCHANGE_RATES))],
)
def create_exchange_rate_endpoint(
    data: ExchangeRateCreate,
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> ExchangeRateRead:
    rate = create_exchange_rate(session=session, data=data)
    return ExchangeRateRead.model_validate(rate)


@router.get(
    "/exchange-rates/latest",
    response_model=list[ExchangeRateRead],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_EXCHANGE_RATES))],
)
def get_latest_rates_endpoint(
    session: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> list[ExchangeRateRead]:
    return [ExchangeRateRead.model_validate(r) for r in get_latest_rates(session=session)]
