"""Authentication dependencies for FastAPI route protection."""

import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import decode_token
from app.dependencies.db import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT token.

    Raises:
        UnauthorizedException: If token is missing, invalid, or user not found.
    """
    if credentials is None:
        raise UnauthorizedException(detail="Authorization header missing")

    payload = decode_token(credentials.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Invalid token payload")

    # Reject refresh tokens used as access tokens
    if payload.get("type") == "refresh":
        raise UnauthorizedException(detail="Cannot use refresh token for access")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(detail="Invalid user ID in token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundException(detail="User not found")
    if not user.is_active:
        raise UnauthorizedException(detail="User account is deactivated")

    # Store user_id on request state for rate limiting
    request.state.user_id = str(user.id)
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise UnauthorizedException(detail="Inactive user")
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require the current user to have admin role.

    Raises:
        ForbiddenException: If user is not an admin.
    """
    if current_user.role != "admin":
        raise ForbiddenException(detail="Admin access required")
    return current_user
