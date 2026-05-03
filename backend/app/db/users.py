from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.user import User


def get_user_by_email(*, session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def get_user_by_id(*, session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def create_or_update_user_from_google(
    *,
    session: Session,
    email: str,
    full_name: str | None,
    google_id: str | None,
    avatar_url: str | None,
) -> User:
    user = get_user_by_email(session=session, email=email)
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            avatar_url=avatar_url,
        )
        session.add(user)
    else:
        if full_name is not None:
            user.full_name = full_name
        if google_id is not None:
            user.google_id = google_id
        if avatar_url is not None:
            user.avatar_url = avatar_url
    user.last_login_at = datetime.utcnow()
    session.commit()
    session.refresh(user)
    return user
