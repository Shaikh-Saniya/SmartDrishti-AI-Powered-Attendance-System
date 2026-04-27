"""Simple in-memory cache with TTL for embedding lookups."""

import time
from typing import Any


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL expiration.

    Used to cache student embeddings to avoid redundant DB lookups
    during batch face matching within a short time window.
    """

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl_seconds

    def get(self, key: str) -> Any | None:
        """Get a cached value, returning None if expired or missing."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with optional custom TTL."""
        expires_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        """Remove a key from the cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    def cleanup(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        return len(expired)


# Global embedding cache instance (1-hour TTL)
embedding_cache = TTLCache(default_ttl_seconds=3600)
