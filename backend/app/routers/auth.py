from datetime import timedelta
from typing import cast

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.db.users import create_or_update_user_from_google
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserRead
from app.utils.dt import utcnow

router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def _create_access_token(user: User) -> str:
    expire = utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": expire,
    }
    return str(jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


@router.get("/google")
async def login_via_google(request: Request) -> RedirectResponse:
    redirect_uri = request.url_for("auth_via_google_callback")
    return cast(RedirectResponse, await oauth.google.authorize_redirect(request, redirect_uri))


@router.get("/google/callback", name="auth_via_google_callback")
async def auth_via_google_callback(
    request: Request,
    session: Session = Depends(get_session),
) -> RedirectResponse:
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]

    if settings.allowed_emails and userinfo["email"] not in settings.allowed_emails:
        return RedirectResponse(url=f"{settings.frontend_url}/auth/forbidden")

    user = create_or_update_user_from_google(
        session=session,
        email=userinfo["email"],
        full_name=userinfo.get("name"),
        google_id=userinfo.get("sub"),
        avatar_url=userinfo.get("picture"),
    )
    access_token = _create_access_token(user)
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?token={access_token}")


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
