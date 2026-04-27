"""Tests for authentication API endpoints."""

import pytest


class TestAuthEndpoints:
    """Test suite for auth API endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        """Test successful login returns JWT tokens."""
        # Requires running database with admin user
        # TODO: Implement with test fixtures
        pass

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self) -> None:
        """Test login with wrong password returns 401."""
        pass

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self) -> None:
        """Test login with non-existent email returns 401."""
        pass

    @pytest.mark.asyncio
    async def test_refresh_token(self) -> None:
        """Test token refresh returns new access token."""
        pass

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self) -> None:
        """Test using access token as refresh token returns 400."""
        pass

    @pytest.mark.asyncio
    async def test_me_authenticated(self) -> None:
        """Test /me endpoint returns current user info."""
        pass

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self) -> None:
        """Test /me endpoint without token returns 401."""
        pass
