from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.constants import (
    RECONCILE_AMOUNT_TOLERANCE,
    RECONCILE_AUTO_MATCH_MAX_HOURS,
    ApiKeyScope,
)
from app.database import get_session
from app.db.app_constants import (
    get_all_constants,
    invalidate_constant_cache,
    upsert_constant,
)
from app.dependencies.auth import get_current_user, require_scope
from app.models.app_constant import AppConstant
from app.models.user import User
from app.schemas.app_constant import AppConstantRead, AppConstantUpdate

router = APIRouter(tags=["app-constants"])


@dataclass
class _ConstantSpec:
    default: str
    kind: Literal["int_positive", "decimal_nonneg"]
    label: str

    def validate(self, value: str) -> None:
        if self.kind == "int_positive":
            try:
                parsed = Decimal(value)
                if parsed % 1 != 0:
                    raise ValueError
                int_value = int(parsed)
            except (ValueError, InvalidOperation):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{self.label}: значение должно быть целым числом",
                ) from None
            if int_value <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{self.label}: значение должно быть положительным целым числом",
                )
        elif self.kind == "decimal_nonneg":
            try:
                decimal_value = Decimal(value)
            except InvalidOperation:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{self.label}: значение должно быть числом",
                ) from None
            if decimal_value < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{self.label}: значение не может быть отрицательным",
                )


_KNOWN_CONSTANTS: dict[str, _ConstantSpec] = {
    "RECONCILE_AUTO_MATCH_MAX_HOURS": _ConstantSpec(
        default=str(RECONCILE_AUTO_MATCH_MAX_HOURS),
        kind="int_positive",
        label="Макс. часов для автосверки",
    ),
    "RECONCILE_AMOUNT_TOLERANCE": _ConstantSpec(
        default=str(RECONCILE_AMOUNT_TOLERANCE),
        kind="decimal_nonneg",
        label="Допустимое отклонение суммы",
    ),
}


@router.get(
    "/app-constants",
    response_model=list[AppConstantRead],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_APP_CONSTANTS))],
)
def list_constants(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AppConstantRead]:
    stored: dict[str, str] = {
        c.key: c.value for c in get_all_constants(session=session, user_id=current_user.id)
    }
    return [
        AppConstantRead(key=key, value=stored.get(key, spec.default))
        for key, spec in _KNOWN_CONSTANTS.items()
    ]


@router.put(
    "/app-constants/{key}",
    response_model=AppConstantRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_APP_CONSTANTS))],
)
def update_constant(
    key: str,
    body: AppConstantUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AppConstant:
    spec = _KNOWN_CONSTANTS.get(key)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Неизвестная константа: '{key}'",
        )
    spec.validate(body.value)

    row = upsert_constant(session=session, user_id=current_user.id, key=key, value=body.value)
    session.commit()
    invalidate_constant_cache(current_user.id, key)
    return row
