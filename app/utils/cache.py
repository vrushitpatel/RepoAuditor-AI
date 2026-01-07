"""Simple in-memory cache with TTL support and automatic expiration.

This module provides a thread-safe, TTL-based caching system to prevent
duplicate operations like reviewing the same PR multiple times.
"""

import threading
import time
from typing import Any, Dict, Optional, Tuple

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache with TTL support.

    This cache stores key-value pairs with optional time-to-live (TTL).
    Expired entries are automatically removed during get operations and
    periodic cleanup.

    Example:
        ```python
        from app.utils.cache import SimpleCache

        cache = SimpleCache()

        # Set a value with 5 minute TTL
        cache.set("repo/pr/123", "reviewed", ttl_seconds=300)

        # Get the value
        if cache.get("repo/pr/123"):
            print("Already reviewed recently")

        # Delete a specific entry
        cache.delete("repo/pr/123")

        # Clear all entries
        cache.clear()
        ```
    """

    def __init__(self, cleanup_interval_seconds: int = 60) -> None:
        """Initialize the cache.

        Args:
            cleanup_interval_seconds: How often to run automatic cleanup (default: 60)
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()

        # Start automatic cleanup
        self._start_cleanup_thread()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache.

        This method is thread-safe and automatically removes expired entries.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise

        Example:
            ```python
            value = cache.get("repo/pr/123")
            if value:
                print(f"Found cached value: {value}")
            ```
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache[key]

            # Check if expired
            if expiry > 0 and time.time() > expiry:
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
                return None

            logger.debug(f"Cache hit for key: {key}")
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 0) -> None:
        """Set a value in cache with optional TTL.

        This method is thread-safe.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (0 = no expiration)

        Example:
            ```python
            # Cache for 5 minutes
            cache.set("repo/pr/123", "reviewed", ttl_seconds=300)

            # Cache forever (no expiration)
            cache.set("permanent-key", "value", ttl_seconds=0)
            ```
        """
        with self._lock:
            expiry = time.time() + ttl_seconds if ttl_seconds > 0 else 0
            self._cache[key] = (value, expiry)
            logger.debug(
                f"Cache set for key: {key}, TTL: {ttl_seconds}s",
                extra={
                    "extra_fields": {
                        "cache_key": key,
                        "ttl_seconds": ttl_seconds,
                    }
                },
            )

    def delete(self, key: str) -> bool:
        """Delete a value from cache.

        This method is thread-safe.

        Args:
            key: Cache key

        Returns:
            True if the key was deleted, False if it didn't exist

        Example:
            ```python
            if cache.delete("repo/pr/123"):
                print("Cache entry removed")
            ```
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted for key: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cached values.

        This method is thread-safe and removes all entries from the cache.

        Example:
            ```python
            cache.clear()
            print("All cache entries removed")
            ```
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared, {count} entries removed")

    def size(self) -> int:
        """Get the current number of cache entries.

        Returns:
            Number of entries in the cache

        Example:
            ```python
            print(f"Cache has {cache.size()} entries")
            ```
        """
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        This method is automatically called periodically, but can also
        be called manually if needed.

        Returns:
            Number of entries removed

        Example:
            ```python
            removed = cache.cleanup_expired()
            print(f"Removed {removed} expired entries")
            ```
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, expiry) in self._cache.items()
                if expiry > 0 and current_time > expiry
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(
                    f"Cleaned up {len(expired_keys)} expired cache entries",
                    extra={"extra_fields": {"expired_count": len(expired_keys)}},
                )

            return len(expired_keys)

    def _start_cleanup_thread(self) -> None:
        """Start the automatic cleanup background thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup.clear()
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True,
                name="cache-cleanup",
            )
            self._cleanup_thread.start()
            logger.debug(
                f"Cache cleanup thread started (interval: {self._cleanup_interval}s)"
            )

    def _cleanup_worker(self) -> None:
        """Background worker that periodically cleans up expired entries."""
        while not self._stop_cleanup.is_set():
            # Wait for the cleanup interval or until stop is signaled
            if self._stop_cleanup.wait(timeout=self._cleanup_interval):
                break

            try:
                self.cleanup_expired()
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}", exc_info=True)

    def stop_cleanup(self) -> None:
        """Stop the automatic cleanup thread.

        This is useful for graceful shutdown or testing.

        Example:
            ```python
            cache.stop_cleanup()
            print("Cleanup thread stopped")
            ```
        """
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
            logger.debug("Cache cleanup thread stopped")

    def __del__(self) -> None:
        """Cleanup when the cache object is destroyed."""
        self.stop_cleanup()

    def __len__(self) -> int:
        """Get the number of cache entries."""
        return self.size()

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in cache (and is not expired).

        Example:
            ```python
            if "repo/pr/123" in cache:
                print("Key exists in cache")
            ```
        """
        return self.get(key) is not None


# Global cache instance for application-wide use
cache = SimpleCache()


def get_cache() -> SimpleCache:
    """Get the global cache instance.

    Returns:
        Global SimpleCache instance

    Example:
        ```python
        from app.utils.cache import get_cache

        cache = get_cache()
        cache.set("key", "value", ttl_seconds=300)
        ```
    """
    return cache
