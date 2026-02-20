"""
TTL-based tool result cache for the Chatterbox agentic loop.

Provides ``ToolResultCache`` (a lightweight time-to-live store) and
``CachingDispatcher`` (a wrapper that caches tool results to avoid redundant
calls).  Both are designed to integrate transparently with the dispatcher
protocol expected by ``AgenticLoop``.

Typical usage::

    from chatterbox.conversation.tools.cache import ToolResultCache, CachingDispatcher

    cache = ToolResultCache(ttl=300.0)   # 5-minute TTL
    base_dispatcher = registry.build_dispatcher()
    cached_dispatcher = CachingDispatcher(base_dispatcher, cache)

    loop = AgenticLoop(provider=provider, tool_dispatcher=cached_dispatcher)

Tools that return non-deterministic results (e.g. random numbers) should NOT
be cached, or the cache should be configured with a short TTL.  The weather
tool and datetime tool have predictable 5-minute / 60-second TTL windows that
make caching cost-effective for typical voice assistant query rates.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

# Matches the ToolDispatcher type alias in loop.py
_DispatcherT = Callable[[str, dict[str, Any]], Awaitable[str]]


class ToolResultCache:
    """Simple TTL-based cache for tool results.

    Results are keyed by ``(tool_name, JSON-serialised-args)`` so that
    identical calls reuse the cached response until *ttl* seconds elapse.

    Args:
        ttl: Seconds before a cached entry expires.  Pass ``0.0`` or a
            negative value to disable caching (every ``get`` returns ``None``).

    Thread/task safety:
        The cache is a plain ``dict`` — safe for single-threaded asyncio use.
        Concurrent writes for the same key are harmless (last writer wins).
    """

    def __init__(self, ttl: float = 300.0) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[str, float]] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(name: str, args: dict[str, Any]) -> str:
        """Return a stable string key for a ``(name, args)`` pair."""
        return name + ":" + json.dumps(args, sort_keys=True, default=str)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(self, name: str, args: dict[str, Any]) -> str | None:
        """Return the cached result for ``(name, args)``, or ``None`` if absent/expired.

        Expired entries are evicted on access (lazy expiry).
        """
        if self._ttl <= 0:
            return None
        key = self._make_key(name, args)
        entry = self._store.get(key)
        if entry is None:
            return None
        result, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            logger.debug("Cache expired: %s", key)
            return None
        logger.debug("Cache hit: %s", key)
        return result

    def put(self, name: str, args: dict[str, Any], result: str) -> None:
        """Store *result* for ``(name, args)`` with the configured TTL."""
        if self._ttl <= 0:
            return
        key = self._make_key(name, args)
        self._store[key] = (result, time.monotonic() + self._ttl)
        logger.debug("Cache stored: %s (ttl=%.1fs)", key, self._ttl)

    def invalidate(self, name: str, args: dict[str, Any] | None = None) -> int:
        """Remove cached entries for *name* (optionally scoped to *args*).

        Args:
            name: Tool name whose cache entries should be removed.
            args: If provided, only the entry for this exact ``(name, args)``
                combination is removed.  If ``None``, all entries for *name*
                are removed.

        Returns:
            Number of entries removed.
        """
        if args is not None:
            key = self._make_key(name, args)
            removed = 1 if self._store.pop(key, None) is not None else 0
        else:
            prefix = name + ":"
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]
            removed = len(keys_to_remove)
        logger.debug("Cache invalidated %d entry/entries for tool %r", removed, name)
        return removed

    def clear(self) -> None:
        """Remove all cached entries."""
        count = len(self._store)
        self._store.clear()
        logger.debug("Cache cleared (%d entries removed)", count)

    def __len__(self) -> int:
        """Return the number of entries currently in the cache (including expired)."""
        return len(self._store)


class CachingDispatcher:
    """A dispatcher wrapper that caches tool results using a ``ToolResultCache``.

    Wraps any dispatcher callable compatible with ``AgenticLoop.tool_dispatcher``
    and transparently serves cached results or delegates to the underlying
    dispatcher on a cache miss.

    Args:
        inner: The underlying async dispatcher ``(name, args) -> str``.
        cache: The ``ToolResultCache`` instance to use.

    Example::

        cache = ToolResultCache(ttl=60.0)
        caching = CachingDispatcher(inner=registry.build_dispatcher(), cache=cache)
        loop = AgenticLoop(provider=provider, tool_dispatcher=caching)
    """

    def __init__(self, inner: _DispatcherT, cache: ToolResultCache) -> None:
        self._inner = inner
        self._cache = cache

    async def __call__(self, name: str, args: dict[str, Any]) -> str:
        """Serve from cache or delegate to inner dispatcher and cache the result."""
        cached = self._cache.get(name, args)
        if cached is not None:
            return cached
        result = await self._inner(name, args)
        self._cache.put(name, args, result)
        return result
