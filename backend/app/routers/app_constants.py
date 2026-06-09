from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.constants import RECONCILE_AMOUNT_TOLERANCE, RECONCILE_AUTO_MATCH_MAX_HOURS
from app.database import get_session
from app.db.app_constants import get_all_constants, upsert_constant
from app.dependencies.auth import get_current_user
from app.models.app_constant import AppConstant
from app.models.user import User
from app.schemas.app_constant import AppConstantRead, AppConstantUpdate

router = APIRouter(tags=["app-constants"])

_DEFAULTS: dict[str, str] = {
    "RECONCILE_AUTO_MATCH_MAX_HOURS": str(RECONCILE_AUTO_MATCH_MAX_HOURS),
    "RECONCILE_AMOUNT_TOLERANCE": str(RECONCILE_AMOUNT_TOLERANCE),
}


@router.get("/app-constants", response_model=list[AppConstantRead])
def list_constants(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AppConstantRead]:
    stored: dict[str, str] = {c.key: c.value for c in get_all_constants(session=session, user_id=current_user.id)}
    return [
        AppConstantRead(key=key, value=stored.get(key, default))
        for key, default in _DEFAULTS.items()
    ]


@router.put("/app-constants/{key}", response_model=AppConstantRead)
def update_constant(
    key: str,
    body: AppConstantUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AppConstant:
    row = upsert_constant(session=session, user_id=current_user.id, key=key, value=body.value)
    session.commit()
    return row
