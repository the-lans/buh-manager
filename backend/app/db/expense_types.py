from uuid import UUID

from sqlmodel import Session, select

from app.models.expense_type import ExpenseType
from app.schemas.expense_type import ExpenseTypeCreate, ExpenseTypeUpdate
from app.utils.ids import scope_user_id


def list_expense_types(*, session: Session, user_id: UUID) -> list[ExpenseType]:
    return list(session.exec(select(ExpenseType).where(ExpenseType.user_id == user_id)).all())


def get_expense_type_by_id(
    *,
    session: Session,
    expense_type_id: str,
    user_id: UUID,
) -> ExpenseType | None:
    scoped_id = scope_user_id(user_id=user_id, public_id=expense_type_id)
    return session.exec(
        select(ExpenseType).where(ExpenseType.id == scoped_id).where(ExpenseType.user_id == user_id)
    ).first()


def create_expense_type(*, session: Session, user_id: UUID, data: ExpenseTypeCreate) -> ExpenseType:
    expense_type = ExpenseType(
        id=scope_user_id(user_id=user_id, public_id=data.id),
        user_id=user_id,
        name=data.name,
        receipt_required=data.receipt_required,
    )
    session.add(expense_type)
    session.commit()
    session.refresh(expense_type)
    return expense_type


def update_expense_type(
    *,
    session: Session,
    expense_type: ExpenseType,
    data: ExpenseTypeUpdate,
) -> ExpenseType:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(expense_type, field, value)
    session.add(expense_type)
    session.commit()
    session.refresh(expense_type)
    return expense_type


def delete_expense_type(*, session: Session, expense_type: ExpenseType) -> None:
    session.delete(expense_type)
    session.commit()
