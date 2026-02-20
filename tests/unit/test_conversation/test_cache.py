"""Unit tests for chatterbox.conversation.tools.cache."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from chatterbox.conversation.tools.cache import CachingDispatcher, ToolResultCache


# ---------------------------------------------------------------------------
# ToolResultCache — basic get/put
# ---------------------------------------------------------------------------


def test_cache_miss_returns_none() -> None:
    cache = ToolResultCache(ttl=60.0)
    assert cache.get("get_weather", {"location": "Kansas"}) is None


def test_cache_hit_returns_stored_value() -> None:
    cache = ToolResultCache(ttl=60.0)
    cache.put("get_weather", {"location": "Kansas"}, '{"temp": 72}')
    assert cache.get("get_weather", {"location": "Kansas"}) == '{"temp": 72}'


def test_cache_different_args_are_separate_entries() -> None:
    cache = ToolResultCache(ttl=60.0)
    cache.put("get_weather", {"location": "Kansas"}, "result_KS")
    cache.put("get_weather", {"location": "Texas"}, "result_TX")
    assert cache.get("get_weather", {"location": "Kansas"}) == "result_KS"
    assert cache.get("get_weather", {"location": "Texas"}) == "result_TX"


def test_cache_different_tool_names_are_separate() -> None:
    cache = ToolResultCache(ttl=60.0)
    cache.put("get_weather", {}, "weather_result")
    cache.put("get_time", {}, "time_result")
    assert cache.get("get_weather", {}) == "weather_result"
    assert cache.get("get_time", {}) == "time_result"


def test_cache_args_order_independent() -> None:
    """JSON serialisation sorts keys so arg order doesn't matter."""
    cache = ToolResultCache(ttl=60.0)
    cache.put("tool", {"b": 2, "a": 1}, "result")
    assert cache.get("tool", {"a": 1, "b": 2}) == "result"


# ---------------------------------------------------------------------------
# ToolResultCache — TTL expiry
# ---------------------------------------------------------------------------


def test_cache_expired_entry_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """An entry past its TTL should be evicted and None returned."""
    import time

    cache = ToolResultCache(ttl=10.0)
    cache.put("get_weather", {}, "fresh")

    # Simulate time passing beyond the TTL
    original_monotonic = time.monotonic
    monkeypatch.setattr(
        "chatterbox.conversation.tools.cache.time.monotonic",
        lambda: original_monotonic() + 11.0,
    )

    assert cache.get("get_weather", {}) is None
    # Expired entry should be evicted
    assert len(cache) == 0


def test_cache_entry_before_expiry_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    cache = ToolResultCache(ttl=10.0)
    cache.put("get_weather", {}, "result")

    original_monotonic = time.monotonic
    monkeypatch.setattr(
        "chatterbox.conversation.tools.cache.time.monotonic",
        lambda: original_monotonic() + 5.0,  # within TTL
    )

    assert cache.get("get_weather", {}) == "result"


# ---------------------------------------------------------------------------
# ToolResultCache — zero/negative TTL disables caching
# ---------------------------------------------------------------------------


def test_zero_ttl_disables_caching() -> None:
    cache = ToolResultCache(ttl=0.0)
    cache.put("get_weather", {}, "result")
    assert cache.get("get_weather", {}) is None


def test_negative_ttl_disables_caching() -> None:
    cache = ToolResultCache(ttl=-1.0)
    cache.put("get_time", {}, "result")
    assert cache.get("get_time", {}) is None


# ---------------------------------------------------------------------------
# ToolResultCache — invalidate and clear
# ---------------------------------------------------------------------------


def test_invalidate_specific_args() -> None:
    cache = ToolResultCache(ttl=60.0)
    cache.put("get_weather", {"location": "Kansas"}, "KS")
    cache.put("get_weather", {"location": "Texas"}, "TX")
    removed = cache.invalidate("get_weather", {"location": "Kansas"})
    assert removed == 1
    assert cache.get("get_weather", {"location": "Kansas"}) is None
    assert cache.get("get_weather", {"location": "Texas"}) == "TX"


def test_invalidate_all_entries_for_tool() -> None:
    cache = ToolResultCache(ttl=60.0)
    cache.put("get_weather", {"location": "Kansas"}, "KS")
    cache.put("get_weather", {"location": "Texas"}, "TX")
    cache.put("get_time", {}, "time")
    removed = cache.invalidate("get_weather")
    assert removed == 2
    assert len(cache) == 1  # only get_time remains


def test_invalidate_nonexistent_args_returns_zero() -> None:
    cache = ToolResultCache(ttl=60.0)
    removed = cache.invalidate("get_weather", {"location": "Nowhere"})
    assert removed == 0


def test_clear_empties_cache() -> None:
    cache = ToolResultCache(ttl=60.0)
    cache.put("a", {}, "1")
    cache.put("b", {}, "2")
    cache.clear()
    assert len(cache) == 0
    assert cache.get("a", {}) is None


def test_len_counts_stored_entries() -> None:
    cache = ToolResultCache(ttl=60.0)
    assert len(cache) == 0
    cache.put("a", {}, "1")
    assert len(cache) == 1
    cache.put("b", {}, "2")
    assert len(cache) == 2


# ---------------------------------------------------------------------------
# CachingDispatcher — cache miss delegates to inner
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_caching_dispatcher_delegates_on_miss() -> None:
    inner = AsyncMock(return_value='{"temp": 72}')
    cache = ToolResultCache(ttl=60.0)
    dispatcher = CachingDispatcher(inner=inner, cache=cache)

    result = await dispatcher("get_weather", {"location": "Kansas"})

    assert result == '{"temp": 72}'
    inner.assert_called_once_with("get_weather", {"location": "Kansas"})


# ---------------------------------------------------------------------------
# CachingDispatcher — cache hit avoids calling inner
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_caching_dispatcher_serves_from_cache_on_hit() -> None:
    inner = AsyncMock(return_value='{"temp": 72}')
    cache = ToolResultCache(ttl=60.0)
    dispatcher = CachingDispatcher(inner=inner, cache=cache)

    # First call — miss, delegates to inner
    result1 = await dispatcher("get_weather", {"location": "Kansas"})
    # Second call — hit, should not call inner again
    result2 = await dispatcher("get_weather", {"location": "Kansas"})

    assert result1 == result2 == '{"temp": 72}'
    inner.assert_called_once()  # inner only called once despite two dispatcher calls


@pytest.mark.anyio
async def test_caching_dispatcher_different_args_call_inner_each_time() -> None:
    inner = AsyncMock(side_effect=["result_KS", "result_TX"])
    cache = ToolResultCache(ttl=60.0)
    dispatcher = CachingDispatcher(inner=inner, cache=cache)

    r1 = await dispatcher("get_weather", {"location": "Kansas"})
    r2 = await dispatcher("get_weather", {"location": "Texas"})

    assert r1 == "result_KS"
    assert r2 == "result_TX"
    assert inner.call_count == 2


@pytest.mark.anyio
async def test_caching_dispatcher_stores_result_after_miss() -> None:
    inner = AsyncMock(return_value="stored_result")
    cache = ToolResultCache(ttl=60.0)
    dispatcher = CachingDispatcher(inner=inner, cache=cache)

    await dispatcher("get_time", {})

    # Cache should now have the result
    assert cache.get("get_time", {}) == "stored_result"


@pytest.mark.anyio
async def test_caching_dispatcher_with_zero_ttl_always_calls_inner() -> None:
    """With TTL=0 the cache is disabled — inner is called every time."""
    inner = AsyncMock(side_effect=["r1", "r2"])
    cache = ToolResultCache(ttl=0.0)
    dispatcher = CachingDispatcher(inner=inner, cache=cache)

    r1 = await dispatcher("get_weather", {})
    r2 = await dispatcher("get_weather", {})

    assert r1 == "r1"
    assert r2 == "r2"
    assert inner.call_count == 2


# ---------------------------------------------------------------------------
# CachingDispatcher — expired entries are re-fetched
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_caching_dispatcher_refetches_after_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    inner = AsyncMock(side_effect=["fresh", "refreshed"])
    cache = ToolResultCache(ttl=5.0)
    dispatcher = CachingDispatcher(inner=inner, cache=cache)

    original_monotonic = time.monotonic

    # First call — miss, caches result
    await dispatcher("get_weather", {})
    assert inner.call_count == 1

    # Advance time past TTL
    monkeypatch.setattr(
        "chatterbox.conversation.tools.cache.time.monotonic",
        lambda: original_monotonic() + 6.0,
    )

    # Second call — entry expired, should delegate to inner again
    result = await dispatcher("get_weather", {})
    assert result == "refreshed"
    assert inner.call_count == 2
