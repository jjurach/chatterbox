"""Unit tests for chatterbox.conversation.entity.ChatterboxConversationEntity."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from chatterbox.conversation.entity import (
    ChatterboxConversationEntity,
    ConversationInput,
    ConversationResult,
)
from chatterbox.conversation.providers import LLMProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(loop_response: str = "Test response") -> ChatterboxConversationEntity:
    """Create an entity with a mocked AgenticLoop."""
    provider = AsyncMock(spec=LLMProvider)

    async def noop_dispatcher(name: str, args: dict[str, Any]) -> str:
        return "tool_result"

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=noop_dispatcher,
    )
    # Patch the loop's run method directly
    entity._loop.run = AsyncMock(return_value=loop_response)
    return entity


# ---------------------------------------------------------------------------
# async_process
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_process_returns_conversation_result() -> None:
    entity = _make_entity("Hello there!")
    user_input = ConversationInput(text="Hi")

    result = await entity.async_process(user_input)

    assert isinstance(result, ConversationResult)
    assert result.response_text == "Hello there!"


@pytest.mark.anyio
async def test_async_process_passes_user_text_to_loop() -> None:
    entity = _make_entity("OK")
    await entity.async_process(ConversationInput(text="What time is it?"))

    entity._loop.run.assert_called_once()
    call_kwargs = entity._loop.run.call_args
    assert call_kwargs.kwargs.get("user_text") == "What time is it?" or \
           call_kwargs.args[0] == "What time is it?"


@pytest.mark.anyio
async def test_async_process_echoes_conversation_id() -> None:
    entity = _make_entity("Response")
    user_input = ConversationInput(text="Hello", conversation_id="sess-42")

    result = await entity.async_process(user_input)

    assert result.conversation_id == "sess-42"


@pytest.mark.anyio
async def test_async_process_no_conversation_id_returns_none() -> None:
    entity = _make_entity("Response")
    result = await entity.async_process(ConversationInput(text="Hello"))

    assert result.conversation_id is None


# ---------------------------------------------------------------------------
# Chat history management
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_multi_turn_history_accumulated() -> None:
    """Second turn should receive the first turn's history."""
    entity = _make_entity("First response")
    input1 = ConversationInput(text="First message", conversation_id="sess-1")
    await entity.async_process(input1)

    entity._loop.run = AsyncMock(return_value="Second response")
    input2 = ConversationInput(text="Second message", conversation_id="sess-1")
    await entity.async_process(input2)

    call_args = entity._loop.run.call_args
    # chat_history should contain the first turn
    history = call_args.kwargs.get("chat_history") or call_args.args[1]
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "First message"}
    assert history[1] == {"role": "assistant", "content": "First response"}


@pytest.mark.anyio
async def test_sessions_are_isolated() -> None:
    """Different conversation_ids must not share history."""
    entity = _make_entity("Resp A")
    await entity.async_process(ConversationInput(text="Session A", conversation_id="A"))

    entity._loop.run = AsyncMock(return_value="Resp B")
    await entity.async_process(ConversationInput(text="Session B", conversation_id="B"))

    # Capture last call args for session B
    call_args = entity._loop.run.call_args
    # Use kwargs if present, else fall back to positional arg 1
    if "chat_history" in call_args.kwargs:
        history = call_args.kwargs["chat_history"]
    else:
        history = call_args.args[1]
    # Session B should have empty history (no spillover from A)
    assert history == []


# ---------------------------------------------------------------------------
# History management methods
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_clear_history_removes_session() -> None:
    entity = _make_entity("R")
    await entity.async_process(ConversationInput(text="Hi", conversation_id="sess-x"))
    assert "sess-x" in entity._histories

    entity.clear_history("sess-x")
    assert "sess-x" not in entity._histories


@pytest.mark.anyio
async def test_clear_all_history() -> None:
    entity = _make_entity("R")
    await entity.async_process(ConversationInput(text="Hi", conversation_id="A"))
    await entity.async_process(ConversationInput(text="Hi", conversation_id="B"))
    assert len(entity._histories) == 2

    entity.clear_all_history()
    assert entity._histories == {}


# ---------------------------------------------------------------------------
# ToolDefinition wiring
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tools_passed_to_loop() -> None:
    from chatterbox.conversation.providers import ToolDefinition

    provider = AsyncMock(spec=LLMProvider)

    async def noop_dispatcher(name: str, args: dict[str, Any]) -> str:
        return "result"

    weather_tool = ToolDefinition(
        name="get_weather",
        description="Get weather",
        parameters={},
    )
    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=noop_dispatcher,
        tools=[weather_tool],
    )
    entity._loop.run = AsyncMock(return_value="Sunny")

    await entity.async_process(ConversationInput(text="Weather?"))

    call_args = entity._loop.run.call_args
    tools_passed = call_args.kwargs.get("tools") or call_args.args[2]
    assert len(tools_passed) == 1
    assert tools_passed[0].name == "get_weather"
