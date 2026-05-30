import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session

from app.config import settings
from app.constants import API_KEY_PREFIX, API_KEY_PREFIX_LENGTH, API_KEY_RANDOM_BYTES
from app.database import get_session
from app.db.api_keys import get_api_key_by_hash, touch_last_used
from app.db.users import get_user_by_id
from app.models.user import User
from app.utils.dt import utcnow

bearer_scheme = HTTPBearer()


def _auth_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@dataclass
class AuthContext:
    user: User
    scopes: frozenset[str] | None  # None = JWT (full access)


def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> AuthContext:
    token = credentials.credentials

    if token.startswith(API_KEY_PREFIX):
        return _auth_via_api_key(token, session)

    return _auth_via_jwt(token, session)


def _auth_via_jwt(token: str, session: Session) -> AuthContext:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise _auth_error()
        user_id = UUID(user_id_str)
    except JWTError as err:
        raise _auth_error() from err
    except ValueError as err:
        raise _auth_error() from err

    user = get_user_by_id(session=session, user_id=user_id)
    if user is None or not user.is_active:
        raise _auth_error()

    return AuthContext(user=user, scopes=None)


def _auth_via_api_key(token: str, session: Session) -> AuthContext:
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    api_key = get_api_key_by_hash(session=session, key_hash=key_hash)

    if api_key is None or not api_key.is_active:
        raise _auth_error()

    if api_key.expires_at is not None and api_key.expires_at < utcnow():
        raise _auth_error()

    user = get_user_by_id(session=session, user_id=api_key.user_id)
    if user is None or not user.is_active:
        raise _auth_error()

    touch_last_used(session=session, api_key=api_key)

    scopes = frozenset(json.loads(api_key.scopes))
    return AuthContext(user=user, scopes=scopes)


def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    return ctx.user


def get_current_user_jwt_only(ctx: AuthContext = Depends(get_auth_context)) -> User:
    if ctx.scopes is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires JWT authentication, not an API key.",
        )
    return ctx.user


def require_scope(scope: str) -> Callable[..., None]:
    def _check(ctx: AuthContext = Depends(get_auth_context)) -> None:
        if ctx.scopes is not None and scope not in ctx.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {scope}",
            )

    return _check


def generate_api_key() -> tuple[str, str, str]:
    """Returns (plaintext_key, key_hash, key_prefix)."""
    random_part = secrets.token_urlsafe(API_KEY_RANDOM_BYTES)
    key = f"{API_KEY_PREFIX}{random_part}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    key_prefix = random_part[:API_KEY_PREFIX_LENGTH]
    return key, key_hash, key_prefix
