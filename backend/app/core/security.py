"""JWT authentication and password hashing utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any

import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def _get_prehash(password: str) -> str:
    """Hash password with SHA-256 to ensure it's under bcrypt's 72-char limit."""
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with 12 rounds (pre-hashed with SHA-256)."""
    return pwd_context.hash(_get_prehash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password (pre-hashed with SHA-256)."""
    return pwd_context.verify(_get_prehash(plain_password), hashed_password)


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: Token subject (typically user ID).
        extra_claims: Additional JWT claims.
        expires_delta: Custom expiration delta.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=settings.JWT_EXPIRY_HOURS))
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a refresh token with extended expiry (7 days)."""
    return create_access_token(
        subject=subject,
        extra_claims={"type": "refresh"},
        expires_delta=timedelta(days=7),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded token payload.

    Raises:
        UnauthorizedException: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("sub") is None:
            raise UnauthorizedException(detail="Invalid token: missing subject")
        return payload
    except JWTError as e:
        raise UnauthorizedException(detail=f"Invalid token: {str(e)}")
