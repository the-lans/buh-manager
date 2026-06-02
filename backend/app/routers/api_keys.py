import json
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.database import get_session
from app.db.api_keys import (
    create_api_key,
    delete_api_key,
    get_api_key_by_id,
    get_api_keys_for_user,
    update_api_key,
)
from app.dependencies.auth import generate_api_key, get_current_user_jwt_only
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead, ApiKeyUpdate
from app.utils.http import get_or_404

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyRead])
def list_api_keys(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_jwt_only),
) -> list[ApiKeyRead]:
    keys = get_api_keys_for_user(session=session, user_id=current_user.id)
    return [_to_read(k) for k in keys]


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key_endpoint(
    data: ApiKeyCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_jwt_only),
) -> ApiKeyCreated:
    plaintext_key, key_hash, key_prefix = generate_api_key()
    scopes = [str(s) for s in data.scopes]

    api_key = create_api_key(
        session=session,
        user_id=current_user.id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes,
        expires_at=data.expires_at,
    )
    session.commit()
    session.refresh(api_key)

    read = _to_read(api_key)
    return ApiKeyCreated(**read.model_dump(), key=plaintext_key)


@router.patch("/{key_id}", response_model=ApiKeyRead)
def update_api_key_endpoint(
    key_id: UUID,
    data: ApiKeyUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_jwt_only),
) -> ApiKeyRead:
    api_key = get_api_key_by_id(session=session, key_id=key_id, user_id=current_user.id)
    api_key = get_or_404(api_key, "API key not found.")
    api_key = update_api_key(session=session, api_key=api_key, data=data)
    session.commit()
    session.refresh(api_key)
    return _to_read(api_key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key_endpoint(
    key_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_jwt_only),
) -> None:
    api_key = get_api_key_by_id(session=session, key_id=key_id, user_id=current_user.id)
    api_key = get_or_404(api_key, "API key not found.")
    delete_api_key(session=session, api_key=api_key)
    session.commit()


def _to_read(api_key: ApiKey) -> ApiKeyRead:
    try:
        scope_list = json.loads(api_key.scopes)
        if not isinstance(scope_list, list):
            raise ValueError("Scopes must be a JSON array")
    except (json.JSONDecodeError, ValueError):
        scope_list = []

    return ApiKeyRead(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=scope_list,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
    )
