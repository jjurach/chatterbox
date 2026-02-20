"""Unit tests for chatterbox.conversation.loop.AgenticLoop."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatterbox.conversation.loop import AgenticLoop
from chatterbox.conversation.providers import (
    CompletionResult,
    ToolCall,
    ToolDefinition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stop_result(text: str) -> CompletionResult:
    """Build a CompletionResult that ends the loop (no tool calls)."""
    return CompletionResult(
        finish_reason="stop",
        content=text,
        tool_calls=[],
        raw_message={"role": "assistant", "content": text},
    )


def _tool_call_result(calls: list[tuple[str, str, dict[str, Any]]]) -> CompletionResult:
    """Build a CompletionResult that requests tool calls.

    Args:
        calls: List of (id, name, arguments) tuples.
    """
    tool_calls = [ToolCall(id=id_, name=name, arguments=args) for id_, name, args in calls]
    raw_tc = [
        {
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
        }
        for tc in tool_calls
    ]
    return CompletionResult(
        finish_reason="tool_calls",
        content=None,
        tool_calls=tool_calls,
        raw_message={"role": "assistant", "tool_calls": raw_tc},
    )


def _make_provider(*results: CompletionResult) -> MagicMock:
    """Return a mock LLMProvider that yields results in sequence."""
    mock = MagicMock()
    mock.complete = AsyncMock(side_effect=list(results))
    return mock


async def _noop_dispatcher(name: str, args: dict[str, Any]) -> str:
    return f"result_of_{name}"


# ---------------------------------------------------------------------------
# Direct response (no tool calls)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_run_returns_text_on_stop() -> None:
    provider = _make_provider(_stop_result("Hello, world!"))
    loop = AgenticLoop(provider=provider, tool_dispatcher=_noop_dispatcher)

    result = await loop.run(user_text="Hi", chat_history=[], tools=[])

    assert result == "Hello, world!"
    provider.complete.assert_called_once()


@pytest.mark.anyio
async def test_run_includes_system_prompt_in_messages() -> None:
    provider = _make_provider(_stop_result("Done"))
    loop = AgenticLoop(
        provider=provider,
        tool_dispatcher=_noop_dispatcher,
        system_prompt="You are helpful.",
    )

    await loop.run(user_text="Test", chat_history=[], tools=[])

    call_args = provider.complete.call_args
    messages = call_args[0][0]
    assert messages[0] == {"role": "system", "content": "You are helpful."}
    assert messages[-1] == {"role": "user", "content": "Test"}


@pytest.mark.anyio
async def test_run_includes_chat_history() -> None:
    provider = _make_provider(_stop_result("Response"))
    loop = AgenticLoop(provider=provider, tool_dispatcher=_noop_dispatcher)

    history = [
        {"role": "user", "content": "Previous"},
        {"role": "assistant", "content": "Prior response"},
    ]
    await loop.run(user_text="New message", chat_history=history, tools=[])

    messages = provider.complete.call_args[0][0]
    # history comes before the new user message
    assert messages[-2] == history[-1]
    assert messages[-1] == {"role": "user", "content": "New message"}


# ---------------------------------------------------------------------------
# Single tool call then stop
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_run_dispatches_single_tool_call() -> None:
    dispatcher = AsyncMock(return_value='{"temp": 72, "conditions": "sunny"}')
    provider = _make_provider(
        _tool_call_result([("call_1", "get_weather", {"location": "Kansas"})]),
        _stop_result("It is 72°F and sunny in Kansas."),
    )

    loop = AgenticLoop(provider=provider, tool_dispatcher=dispatcher)
    result = await loop.run("What's the weather in Kansas?", chat_history=[], tools=[])

    assert result == "It is 72°F and sunny in Kansas."
    dispatcher.assert_called_once_with("get_weather", {"location": "Kansas"})

    # Second LLM call must include the tool result message
    second_call_messages = provider.complete.call_args_list[1][0][0]
    tool_result_msg = next(
        (m for m in second_call_messages if m.get("role") == "tool"), None
    )
    assert tool_result_msg is not None
    assert tool_result_msg["tool_call_id"] == "call_1"
    assert '{"temp": 72' in tool_result_msg["content"]


# ---------------------------------------------------------------------------
# Multiple tool calls in sequence
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_run_handles_multiple_tool_iterations() -> None:
    dispatcher = AsyncMock(side_effect=["weather_result", "time_result"])
    provider = _make_provider(
        _tool_call_result([("c1", "get_weather", {"location": "LA"})]),
        _tool_call_result([("c2", "get_time", {})]),
        _stop_result("Weather and time retrieved."),
    )

    loop = AgenticLoop(provider=provider, tool_dispatcher=dispatcher, max_iterations=5)
    result = await loop.run("Weather and time?", [], [])

    assert result == "Weather and time retrieved."
    assert provider.complete.call_count == 3
    assert dispatcher.call_count == 2


# ---------------------------------------------------------------------------
# Tool dispatcher error handling
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_run_handles_tool_dispatcher_exception() -> None:
    """A failing tool should produce an error JSON result, not crash the loop."""

    async def failing_dispatcher(name: str, args: dict[str, Any]) -> str:
        raise ValueError("API unavailable")

    provider = _make_provider(
        _tool_call_result([("c1", "get_weather", {"location": "X"})]),
        _stop_result("I could not retrieve weather."),
    )

    loop = AgenticLoop(provider=provider, tool_dispatcher=failing_dispatcher)
    result = await loop.run("Weather?", [], [])

    # The loop should not raise; the error is passed back to the LLM as a tool result
    assert result == "I could not retrieve weather."
    second_call_messages = provider.complete.call_args_list[1][0][0]
    tool_msg = next(m for m in second_call_messages if m.get("role") == "tool")
    assert "error" in tool_msg["content"]
    assert "API unavailable" in tool_msg["content"]


# ---------------------------------------------------------------------------
# max_iterations guard
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_run_raises_on_max_iterations_exceeded() -> None:
    """Loop must raise RuntimeError if LLM never stops calling tools."""
    # Always return a tool call — never stops
    provider = MagicMock()
    provider.complete = AsyncMock(
        return_value=_tool_call_result([("c1", "forever", {})])
    )

    loop = AgenticLoop(
        provider=provider, tool_dispatcher=_noop_dispatcher, max_iterations=3
    )

    with pytest.raises(RuntimeError, match="max_iterations"):
        await loop.run("Loop forever", [], [])

    assert provider.complete.call_count == 3


# ---------------------------------------------------------------------------
# Tool definitions are passed to provider
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_run_passes_tool_definitions_to_provider() -> None:
    provider = _make_provider(_stop_result("ok"))
    loop = AgenticLoop(provider=provider, tool_dispatcher=_noop_dispatcher)

    tool = ToolDefinition(
        name="get_weather",
        description="Get weather",
        parameters={"type": "object", "properties": {"location": {"type": "string"}}},
    )

    await loop.run("test", [], [tool])

    _, tools_arg = provider.complete.call_args[0]
    assert len(tools_arg) == 1
    assert tools_arg[0].name == "get_weather"
