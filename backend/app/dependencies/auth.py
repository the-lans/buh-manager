from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.db.users import get_user_by_id
from app.models.user import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    token = credentials.credentials
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise auth_error
    except JWTError as err:
        raise auth_error from err

    user = get_user_by_id(session=session, user_id=UUID(user_id_str))
    if user is None or not user.is_active:
        raise auth_error
    return user
