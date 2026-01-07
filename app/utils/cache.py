"""In-memory caching utilities."""

import time
from typing import Any, Dict, Optional, Tuple


class InMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]

        # Check if expired
        if expiry > 0 and time.time() > expiry:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (0 = no expiration)
        """
        expiry = time.time() + ttl if ttl > 0 else 0
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """
        Delete a value from cache.

        Args:
            key: Cache key
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, expiry) in self._cache.items()
            if expiry > 0 and current_time > expiry
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


# Global cache instance
cache = InMemoryCache()
