from uuid import UUID

from sqlmodel import Session, func, select

from app.models.account import Account
from app.models.balance import Balance
from app.schemas.account import AccountCreate, AccountUpdate


def get_accounts_for_user(*, session: Session, user_id: UUID) -> list[Account]:
    return list(session.exec(select(Account).where(Account.user_id == user_id)).all())


def get_account_by_id(
    *,
    session: Session,
    account_id: UUID,
    user_id: UUID,
) -> Account | None:
    return session.exec(
        select(Account)
        .where(Account.id == account_id)
        .where(Account.user_id == user_id)
    ).first()


def has_balances_for_account(*, session: Session, account_id: UUID) -> bool:
    count = session.exec(
        select(func.count()).where(Balance.account_id == account_id)
    ).one()
    return count > 0


def create_account(*, session: Session, user_id: UUID, data: AccountCreate) -> Account:
    account = Account(
        user_id=user_id,
        bank=data.bank,
        account_number=data.account_number,
        currency=data.currency,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def update_account(
    *,
    session: Session,
    account: Account,
    data: AccountUpdate,
) -> Account:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def delete_account(*, session: Session, account: Account) -> None:
    session.delete(account)
    session.commit()
