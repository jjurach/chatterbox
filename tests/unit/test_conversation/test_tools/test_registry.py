"""Unit tests for chatterbox.conversation.tools.registry.ToolRegistry."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from chatterbox.conversation.providers import ToolDefinition
from chatterbox.conversation.tools.registry import AsyncToolHandler, ToolRegistry

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_DEF_A = ToolDefinition(
    name="tool_a",
    description="First test tool.",
    parameters={"type": "object", "properties": {}, "required": []},
)

_DEF_B = ToolDefinition(
    name="tool_b",
    description="Second test tool.",
    parameters={"type": "object", "properties": {}, "required": []},
)


async def _ok_handler(args: dict[str, Any]) -> str:
    return json.dumps({"status": "ok", "args": args})


async def _raise_handler(args: dict[str, Any]) -> str:
    raise ValueError("handler error")


async def _timeout_handler(args: dict[str, Any]) -> str:
    await asyncio.sleep(999)  # simulate hung tool
    return json.dumps({"status": "ok"})


# ---------------------------------------------------------------------------
# ToolRegistry — registration
# ---------------------------------------------------------------------------


class TestToolRegistryRegistration:
    def test_register_single_tool(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        assert "tool_a" in registry
        assert len(registry) == 1

    def test_register_multiple_tools(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        registry.register(_DEF_B, _ok_handler)
        assert len(registry) == 2

    def test_duplicate_registration_raises(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_DEF_A, _ok_handler)

    def test_contains_false_for_unknown(self) -> None:
        registry = ToolRegistry()
        assert "nonexistent" not in registry

    def test_deregister_removes_tool(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        registry.deregister("tool_a")
        assert "tool_a" not in registry
        assert len(registry) == 0

    def test_deregister_unknown_raises(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(KeyError):
            registry.deregister("nonexistent")

    def test_deregister_then_reregister(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        registry.deregister("tool_a")
        registry.register(_DEF_A, _ok_handler)  # should not raise
        assert "tool_a" in registry


# ---------------------------------------------------------------------------
# ToolRegistry — get_definitions
# ---------------------------------------------------------------------------


class TestToolRegistryDefinitions:
    def test_empty_registry_returns_empty_list(self) -> None:
        assert ToolRegistry().get_definitions() == []

    def test_definitions_reflect_registered_tools(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        registry.register(_DEF_B, _ok_handler)
        defns = registry.get_definitions()
        assert len(defns) == 2
        names = {d.name for d in defns}
        assert names == {"tool_a", "tool_b"}

    def test_definitions_preserve_insertion_order(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        registry.register(_DEF_B, _ok_handler)
        defns = registry.get_definitions()
        assert defns[0].name == "tool_a"
        assert defns[1].name == "tool_b"


# ---------------------------------------------------------------------------
# ToolRegistry — build_dispatcher: basic dispatch
# ---------------------------------------------------------------------------


class TestDispatcherBasicDispatch:
    @pytest.mark.anyio
    async def test_successful_dispatch(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        dispatch = registry.build_dispatcher(timeout=None)
        result = await dispatch("tool_a", {"x": 1})
        assert json.loads(result) == {"status": "ok", "args": {"x": 1}}

    @pytest.mark.anyio
    async def test_unknown_tool_returns_error_json(self) -> None:
        registry = ToolRegistry()
        dispatch = registry.build_dispatcher(timeout=None)
        result = await dispatch("unknown", {})
        data = json.loads(result)
        assert "error" in data
        assert "unknown" in data["error"].lower() or "Unknown" in data["error"]

    @pytest.mark.anyio
    async def test_non_retryable_exception_propagates(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _raise_handler)
        dispatch = registry.build_dispatcher(timeout=None, max_retries=0)
        with pytest.raises(ValueError, match="handler error"):
            await dispatch("tool_a", {})

    @pytest.mark.anyio
    async def test_snapshot_at_build_time(self) -> None:
        """Tools registered after build_dispatcher() are not visible to it."""
        registry = ToolRegistry()
        registry.register(_DEF_A, _ok_handler)
        dispatch = registry.build_dispatcher(timeout=None)
        registry.register(_DEF_B, _ok_handler)
        # _DEF_B was added after snapshot — should be unknown
        result = await dispatch("tool_b", {})
        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# ToolRegistry — build_dispatcher: timeout
# ---------------------------------------------------------------------------


class TestDispatcherTimeout:
    @pytest.mark.anyio
    async def test_timeout_raises_asyncio_timeout_error(self) -> None:
        registry = ToolRegistry()
        registry.register(_DEF_A, _timeout_handler)
        dispatch = registry.build_dispatcher(timeout=0.01, max_retries=0)
        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await dispatch("tool_a", {})

    @pytest.mark.anyio
    async def test_no_timeout_allows_slow_handler(self) -> None:
        """With timeout=None a quick handler still works."""
        call_count = 0

        async def _fast(args: dict[str, Any]) -> str:
            nonlocal call_count
            call_count += 1
            return json.dumps({"ok": True})

        registry = ToolRegistry()
        registry.register(_DEF_A, _fast)
        dispatch = registry.build_dispatcher(timeout=None)
        result = await dispatch("tool_a", {})
        assert json.loads(result) == {"ok": True}
        assert call_count == 1


# ---------------------------------------------------------------------------
# ToolRegistry — build_dispatcher: retry
# ---------------------------------------------------------------------------


class TestDispatcherRetry:
    @pytest.mark.anyio
    async def test_retry_on_matching_exception(self) -> None:
        attempts = 0

        async def _flaky(args: dict[str, Any]) -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise asyncio.TimeoutError("simulated timeout")
            return json.dumps({"ok": True})

        registry = ToolRegistry()
        registry.register(_DEF_A, _flaky)
        dispatch = registry.build_dispatcher(
            timeout=None,
            max_retries=2,
            retry_exceptions=(asyncio.TimeoutError,),
        )
        result = await dispatch("tool_a", {})
        assert json.loads(result) == {"ok": True}
        assert attempts == 3

    @pytest.mark.anyio
    async def test_retry_exhausted_propagates_last_exception(self) -> None:
        attempts = 0

        async def _always_timeout(args: dict[str, Any]) -> str:
            nonlocal attempts
            attempts += 1
            raise asyncio.TimeoutError("always timeout")

        registry = ToolRegistry()
        registry.register(_DEF_A, _always_timeout)
        dispatch = registry.build_dispatcher(
            timeout=None,
            max_retries=2,
            retry_exceptions=(asyncio.TimeoutError,),
        )
        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await dispatch("tool_a", {})
        assert attempts == 3  # 1 original + 2 retries

    @pytest.mark.anyio
    async def test_non_matching_exception_not_retried(self) -> None:
        attempts = 0

        async def _value_error(args: dict[str, Any]) -> str:
            nonlocal attempts
            attempts += 1
            raise ValueError("not a timeout")

        registry = ToolRegistry()
        registry.register(_DEF_A, _value_error)
        dispatch = registry.build_dispatcher(
            timeout=None,
            max_retries=3,
            retry_exceptions=(asyncio.TimeoutError,),
        )
        with pytest.raises(ValueError):
            await dispatch("tool_a", {})
        assert attempts == 1  # no retries for non-matching exception

    @pytest.mark.anyio
    async def test_zero_retries_is_single_attempt(self) -> None:
        attempts = 0

        async def _always_timeout(args: dict[str, Any]) -> str:
            nonlocal attempts
            attempts += 1
            raise asyncio.TimeoutError("timeout")

        registry = ToolRegistry()
        registry.register(_DEF_A, _always_timeout)
        dispatch = registry.build_dispatcher(
            timeout=None,
            max_retries=0,
            retry_exceptions=(asyncio.TimeoutError,),
        )
        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await dispatch("tool_a", {})
        assert attempts == 1
