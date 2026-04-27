"""In-memory sliding window rate limiter as a FastAPI dependency."""

import time
from collections import defaultdict

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitException


class RateLimiter:
    """Sliding window rate limiter.

    Tracks request timestamps per user (by IP or user ID) and enforces
    a maximum number of requests within a 60-second window.
    """

    def __init__(self) -> None:
        # {identifier: [timestamps]}
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, key: str, window: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = time.monotonic() - window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check(self, identifier: str, max_requests: int, window: float = 60.0) -> None:
        """Check if the identifier is within rate limits.

        Args:
            identifier: Unique key for the requester.
            max_requests: Maximum allowed requests in the window.
            window: Time window in seconds (default: 60).

        Raises:
            RateLimitException: If rate limit exceeded.
        """
        self._cleanup(identifier, window)
        if len(self._requests[identifier]) >= max_requests:
            raise RateLimitException(
                detail=f"Rate limit exceeded: {max_requests} requests per {int(window)}s"
            )
        self._requests[identifier].append(time.monotonic())


# Global rate limiter instance
_rate_limiter = RateLimiter()


def _get_identifier(request: Request) -> str:
    """Extract a unique identifier from the request (user ID or IP)."""
    # Try to use authenticated user ID if available
    user = getattr(request.state, "user_id", None)
    if user:
        return f"user:{user}"
    # Fall back to client IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


async def rate_limit_upload(request: Request) -> None:
    """Rate limit dependency for upload endpoints (10/min per user)."""
    identifier = _get_identifier(request)
    _rate_limiter.check(
        identifier=f"upload:{identifier}",
        max_requests=settings.RATE_LIMIT_UPLOAD,
    )


async def rate_limit_default(request: Request) -> None:
    """Rate limit dependency for general endpoints (100/min per user)."""
    identifier = _get_identifier(request)
    _rate_limiter.check(
        identifier=f"default:{identifier}",
        max_requests=settings.RATE_LIMIT_DEFAULT,
    )
