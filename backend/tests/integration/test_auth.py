from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from app.config import settings
from app.models.user import User


@pytest.mark.asyncio
async def test_get_me_with_valid_token(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_user: User,
) -> None:
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_me_without_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_expired_token(client: AsyncClient, test_user: User) -> None:
    expired_token = jwt.encode(
        {"sub": str(test_user.id), "exp": datetime.utcnow() - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_non_uuid_sub_returns_401(client: AsyncClient) -> None:
    """JWT with a non-UUID 'sub' must return 401, not 500 (ValueError guard)."""
    token = jwt.encode(
        {"sub": "not-a-uuid", "exp": datetime.utcnow() + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
