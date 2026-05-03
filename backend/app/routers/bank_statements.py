from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.bank_statement import BankStatementCreate, ImportReport
from app.services.import_statement import import_bank_statement

router = APIRouter(prefix="/bank-statements", tags=["bank-statements"])


@router.post("", response_model=ImportReport, status_code=status.HTTP_200_OK)
def import_statement(
    data: BankStatementCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ImportReport:
    return import_bank_statement(
        session=session,
        statement=data,
        current_user=current_user,
    )
