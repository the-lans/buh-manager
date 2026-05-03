from sqlmodel import Session, select

from app.models.expense_type import ExpenseType
from app.schemas.expense_type import ExpenseTypeCreate, ExpenseTypeUpdate


def list_expense_types(*, session: Session) -> list[ExpenseType]:
    return list(session.exec(select(ExpenseType)).all())


def get_expense_type_by_id(*, session: Session, expense_type_id: str) -> ExpenseType | None:
    return session.get(ExpenseType, expense_type_id)


def create_expense_type(*, session: Session, data: ExpenseTypeCreate) -> ExpenseType:
    expense_type = ExpenseType(
        id=data.id,
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
