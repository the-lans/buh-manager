from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt

from app.config import settings
from app.models.user import User
from app.utils.dt import utcnow

_GOOGLE_USERINFO = {
    "email": "allowed@example.com",
    "name": "Allowed User",
    "sub": "google-123",
    "picture": "https://example.com/pic.jpg",
}


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
        {"sub": str(test_user.id), "exp": utcnow() - timedelta(minutes=1)},
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
        {"sub": "not-a-uuid", "exp": utcnow() + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# ── Google OAuth callback whitelist ──────────────────────────────────────────

def _mock_oauth(userinfo: dict) -> AsyncMock:
    return AsyncMock(return_value={"userinfo": userinfo})


@pytest.mark.asyncio
async def test_google_callback_blocks_disallowed_email(client: AsyncClient) -> None:
    userinfo = {**_GOOGLE_USERINFO, "email": "blocked@evil.com"}
    with patch("app.routers.auth.oauth.google.authorize_access_token", new=_mock_oauth(userinfo)):
        with patch.object(settings, "allowed_emails", ["allowed@example.com"]):
            response = await client.get("/api/v1/auth/google/callback")
    assert response.status_code in (302, 307)
    assert response.headers["location"].endswith("/auth/forbidden")


@pytest.mark.asyncio
async def test_google_callback_allows_whitelisted_email(client: AsyncClient) -> None:
    with patch("app.routers.auth.oauth.google.authorize_access_token", new=_mock_oauth(_GOOGLE_USERINFO)):
        with patch.object(settings, "allowed_emails", ["allowed@example.com"]):
            response = await client.get("/api/v1/auth/google/callback")
    assert response.status_code in (302, 307)
    assert "/auth/forbidden" not in response.headers["location"]


@pytest.mark.asyncio
async def test_google_callback_allows_any_email_when_whitelist_empty(client: AsyncClient) -> None:
    userinfo = {**_GOOGLE_USERINFO, "email": "anyone@random.com"}
    with patch("app.routers.auth.oauth.google.authorize_access_token", new=_mock_oauth(userinfo)):
        with patch.object(settings, "allowed_emails", []):
            response = await client.get("/api/v1/auth/google/callback")
    assert response.status_code in (302, 307)
    assert "/auth/forbidden" not in response.headers["location"]
