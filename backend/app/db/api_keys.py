import json
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyUpdate


def create_api_key(
    *,
    session: Session,
    user_id: UUID,
    name: str,
    key_hash: str,
    key_prefix: str,
    scopes: list[str],
    expires_at: datetime | None,
) -> ApiKey:
    api_key = ApiKey(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=json.dumps(scopes),
        expires_at=expires_at,
    )
    session.add(api_key)
    return api_key


def get_api_key_by_hash(*, session: Session, key_hash: str) -> ApiKey | None:
    return session.exec(select(ApiKey).where(ApiKey.key_hash == key_hash)).first()


def get_api_keys_for_user(*, session: Session, user_id: UUID) -> list[ApiKey]:
    return list(
        session.exec(
            select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())  # type: ignore[attr-defined]
        ).all()
    )


def get_api_key_by_id(*, session: Session, key_id: UUID, user_id: UUID) -> ApiKey | None:
    return session.exec(
        select(ApiKey).where(ApiKey.id == key_id).where(ApiKey.user_id == user_id)
    ).first()


def update_api_key(*, session: Session, api_key: ApiKey, data: ApiKeyUpdate) -> ApiKey:
    if data.name is not None:
        api_key.name = data.name
    if data.scopes is not None:
        api_key.scopes = json.dumps([str(s) for s in data.scopes])
    if data.is_active is not None:
        api_key.is_active = data.is_active
    session.add(api_key)
    return api_key


def delete_api_key(*, session: Session, api_key: ApiKey) -> None:
    session.delete(api_key)


def touch_last_used(*, session: Session, api_key: ApiKey) -> None:
    api_key.last_used_at = datetime.utcnow()
    session.add(api_key)
