"""End-to-end integration tests for the Chatterbox conversation pipeline.

These tests exercise the full text-in → agentic-loop → text-out pathway
via the conversation HTTP server.  No real LLM or Wyoming server is required;
the AgenticLoop is wired with a mock provider so tests run quickly and offline.

For a full hardware-in-the-loop test (Whisper STT → conversation server →
Piper TTS), see the Emulator integration in tests/integration/test_whisper_stt.py
and tests/integration/test_piper_tts.py.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from chatterbox.conversation.entity import (
    ChatterboxConversationEntity,
    ConversationInput,
)
from chatterbox.conversation.providers import (
    CompletionResult,
    LLMAPIError,
    LLMConnectionError,
    LLMProvider,
    LLMRateLimitError,
    ToolCall,
)
from chatterbox.conversation.server import create_conversation_app
from chatterbox.conversation.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_entity(response: str = "Test response") -> ChatterboxConversationEntity:
    """Return a conversation entity with a mocked agentic loop."""
    provider = AsyncMock(spec=LLMProvider)

    async def noop_dispatcher(name: str, args: dict[str, Any]) -> str:
        return "result"

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=noop_dispatcher,
        auto_create_conversation_id=True,
    )
    entity._loop.run = AsyncMock(return_value=response)
    return entity


# ---------------------------------------------------------------------------
# Full pipeline: text in → server → text out
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_conversation_server_single_turn() -> None:
    """Server processes a single-turn request end-to-end."""
    entity = _make_entity("It is 72°F and sunny in Kansas City.")
    app = create_conversation_app(entity)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/conversation",
            json={"text": "What is the weather in Kansas City?"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "sunny" in body["response_text"]


@pytest.mark.anyio
async def test_conversation_server_auto_creates_session_id() -> None:
    """Server auto-creates a conversation_id when not supplied."""
    entity = _make_entity("Hello!")
    app = create_conversation_app(entity)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/conversation", json={"text": "Hi"})
    body = resp.json()
    assert body["conversation_id"] is not None
    assert len(body["conversation_id"]) == 36  # UUID4


@pytest.mark.anyio
async def test_conversation_server_multi_turn_context() -> None:
    """Multi-turn session retains history across successive requests."""
    entity = _make_entity("I'm doing well, thanks!")
    app = create_conversation_app(entity)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First turn — let server create a session ID
        resp1 = await client.post("/conversation", json={"text": "Hello"})
        assert resp1.status_code == 200
        session_id = resp1.json()["conversation_id"]
        assert session_id is not None

        # Second turn — reuse same session
        entity._loop.run.return_value = "Kansas City, Missouri."
        resp2 = await client.post(
            "/conversation",
            json={"text": "What city am I in?", "conversation_id": session_id},
        )
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == session_id

    # History should contain 2 turns (4 messages: user+assistant ×2)
    assert len(entity._histories[session_id]) == 4


@pytest.mark.anyio
async def test_conversation_server_health_reflects_sessions() -> None:
    """Health endpoint tracks active sessions correctly."""
    entity = _make_entity("Hi")
    app = create_conversation_app(entity)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        h1 = await client.get("/health")
        assert h1.json()["active_sessions"] == 0

        await client.post("/conversation", json={"text": "Hello"})

        h2 = await client.get("/health")
        assert h2.json()["active_sessions"] == 1


@pytest.mark.anyio
async def test_conversation_server_clear_session() -> None:
    """Deleting a session removes its history from memory."""
    entity = _make_entity("Bye!")
    app = create_conversation_app(entity)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/conversation",
            json={"text": "Hello", "conversation_id": "test-clear"},
        )
        assert "test-clear" in entity._histories

        del_resp = await client.delete("/conversation/test-clear")
        assert del_resp.status_code == 204

    assert "test-clear" not in entity._histories


@pytest.mark.anyio
async def test_conversation_server_with_tool_registry() -> None:
    """Conversation server works when entity is initialised with a ToolRegistry."""
    registry = ToolRegistry()
    # No tools registered — dispatcher will never be called for direct responses
    provider = AsyncMock(spec=LLMProvider)

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=registry.build_dispatcher(),
        tools=registry.get_definitions(),
    )
    entity._loop.run = AsyncMock(return_value="Why did the chicken cross the road?")

    app = create_conversation_app(entity)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/conversation", json={"text": "Tell me a joke"})
    assert resp.status_code == 200
    assert "chicken" in resp.json()["response_text"]


@pytest.mark.anyio
async def test_full_pipeline_text_flow() -> None:
    """Simulate the STT-text → conversation server → TTS-text pipeline.

    This test mirrors what Home Assistant does:
      1. STT produces transcript text.
      2. HA calls Conversation Agent (our server) with that text.
      3. Agent returns response text.
      4. HA feeds response text to TTS.

    Here STT and TTS are represented by plain strings; no Wyoming services
    are required.  The goal is to validate the conversation layer alone.
    """
    # Pretend Whisper produced this transcript
    stt_transcript = "What is the weather in Kansas City today?"
    # Expected agent response
    expected_response = "Currently 68°F, partly cloudy in Kansas City."

    entity = _make_entity(expected_response)
    app = create_conversation_app(entity)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: HA sends STT transcript to conversation agent
        resp = await client.post("/conversation", json={"text": stt_transcript})

    assert resp.status_code == 200
    body = resp.json()

    # Step 2: Conversation agent returns text for TTS
    tts_input = body["response_text"]
    assert tts_input == expected_response


# ---------------------------------------------------------------------------
# Tool-calling through the real AgenticLoop (Task 4.12)
# ---------------------------------------------------------------------------


def _tool_call_result(
    call_id: str, name: str, arguments: dict[str, Any]
) -> CompletionResult:
    """Return a CompletionResult that requests one tool call."""
    raw_message: dict[str, Any] = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments),
                },
            }
        ],
    }
    return CompletionResult(
        finish_reason="tool_calls",
        content=None,
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
        raw_message=raw_message,
    )


def _stop_result(text: str) -> CompletionResult:
    """Return a CompletionResult with a final text response."""
    return CompletionResult(
        finish_reason="stop",
        content=text,
        tool_calls=[],
        raw_message={"role": "assistant", "content": text},
    )


@pytest.mark.anyio
async def test_agentic_loop_weather_tool_calling() -> None:
    """AgenticLoop dispatches a weather tool call and returns the final response.

    Validates the full tool-calling pathway:
      user text → LLM requests tool → dispatcher called → LLM final response.
    """
    weather_response = "It's 72°F and sunny in Kansas City, Missouri."

    provider = AsyncMock(spec=LLMProvider)
    provider.complete.side_effect = [
        _tool_call_result("call-1", "get_weather", {"location": "Kansas City, MO"}),
        _stop_result(weather_response),
    ]

    dispatcher_calls: list[tuple[str, dict[str, Any]]] = []

    async def mock_weather_dispatcher(name: str, args: dict[str, Any]) -> str:
        dispatcher_calls.append((name, args))
        return json.dumps({"temperature_f": 72, "conditions": "sunny"})

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=mock_weather_dispatcher,
    )

    result = await entity.async_process(
        ConversationInput(text="What is the weather in Kansas City?")
    )

    assert result.response_text == weather_response
    assert len(dispatcher_calls) == 1
    name, args = dispatcher_calls[0]
    assert name == "get_weather"
    assert args == {"location": "Kansas City, MO"}
    assert provider.complete.call_count == 2


@pytest.mark.anyio
async def test_agentic_loop_datetime_tool_calling() -> None:
    """AgenticLoop dispatches a datetime tool call and uses the result."""
    final_response = "The current time is 3:45 PM Eastern Time."

    provider = AsyncMock(spec=LLMProvider)
    provider.complete.side_effect = [
        _tool_call_result("call-dt", "get_current_datetime", {"timezone": "America/New_York"}),
        _stop_result(final_response),
    ]

    dispatched: list[str] = []

    async def mock_dt_dispatcher(name: str, args: dict[str, Any]) -> str:
        dispatched.append(name)
        return json.dumps({"datetime": "2026-02-20T15:45:00-05:00", "timezone": "America/New_York"})

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=mock_dt_dispatcher,
    )

    result = await entity.async_process(ConversationInput(text="What time is it?"))

    assert result.response_text == final_response
    assert dispatched == ["get_current_datetime"]


@pytest.mark.anyio
async def test_agentic_loop_multi_tool_sequence() -> None:
    """AgenticLoop handles two sequential tool calls in one conversation turn."""
    final_response = "The weather in Kansas City is 72°F, and it is 3:00 PM local time."

    provider = AsyncMock(spec=LLMProvider)
    provider.complete.side_effect = [
        _tool_call_result("call-w", "get_weather", {"location": "Kansas City"}),
        _tool_call_result("call-t", "get_current_datetime", {"timezone": "America/Chicago"}),
        _stop_result(final_response),
    ]

    dispatched: list[str] = []

    async def mock_dispatcher(name: str, args: dict[str, Any]) -> str:
        dispatched.append(name)
        if name == "get_weather":
            return json.dumps({"temperature_f": 72, "conditions": "partly cloudy"})
        return json.dumps({"datetime": "2026-02-20T15:00:00-06:00"})

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=mock_dispatcher,
    )

    result = await entity.async_process(ConversationInput(text="Weather and time in Kansas City?"))

    assert result.response_text == final_response
    assert dispatched == ["get_weather", "get_current_datetime"]
    assert provider.complete.call_count == 3


# ---------------------------------------------------------------------------
# Error scenario tests (Task 4.12)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_llm_rate_limit_returns_graceful_response() -> None:
    """Rate limit error from the LLM returns a human-readable degradation message."""
    provider = AsyncMock(spec=LLMProvider)
    provider.complete.side_effect = LLMRateLimitError("Too many requests")

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=AsyncMock(return_value="unused"),
    )

    result = await entity.async_process(ConversationInput(text="What time is it?"))

    assert "too many requests" in result.response_text.lower()


@pytest.mark.anyio
async def test_llm_connection_error_returns_graceful_response() -> None:
    """LLM connection failure returns a human-readable error message."""
    provider = AsyncMock(spec=LLMProvider)
    provider.complete.side_effect = LLMConnectionError("Connection refused")

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=AsyncMock(return_value="unused"),
    )

    result = await entity.async_process(ConversationInput(text="Tell me a joke"))

    assert "can't reach" in result.response_text.lower() or "connection" in result.response_text.lower()


@pytest.mark.anyio
async def test_llm_api_error_returns_graceful_response() -> None:
    """Generic LLM API error returns a human-readable error message."""
    provider = AsyncMock(spec=LLMProvider)
    provider.complete.side_effect = LLMAPIError("Internal server error", status_code=500)

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=AsyncMock(return_value="unused"),
    )

    result = await entity.async_process(ConversationInput(text="What is the weather?"))

    assert "error" in result.response_text.lower()


@pytest.mark.anyio
async def test_max_iterations_exceeded_returns_graceful_response() -> None:
    """If the LLM keeps requesting tools without stopping, entity returns graceful error.

    Uses max_iterations=2 so the loop exhausts after 2 calls.
    """
    # Provider always returns a tool call, never "stop" — should trip the iteration guard.
    provider = AsyncMock(spec=LLMProvider)
    provider.complete.return_value = _tool_call_result(
        "call-x", "loop_forever", {"x": 1}
    )

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=AsyncMock(return_value="result"),
        max_iterations=2,
    )

    result = await entity.async_process(ConversationInput(text="Infinite loop"))

    assert "stuck" in result.response_text.lower() or "error" in result.response_text.lower()


@pytest.mark.anyio
async def test_tool_failure_does_not_crash_loop() -> None:
    """A dispatcher exception is caught; the loop continues and produces a response."""
    final_response = "I encountered an issue with that tool, but here is what I can tell you."

    provider = AsyncMock(spec=LLMProvider)
    provider.complete.side_effect = [
        _tool_call_result("call-fail", "broken_tool", {}),
        _stop_result(final_response),
    ]

    async def failing_dispatcher(name: str, args: dict[str, Any]) -> str:
        raise RuntimeError("Simulated tool failure")

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=failing_dispatcher,
    )

    result = await entity.async_process(ConversationInput(text="Use the broken tool"))

    assert result.response_text == final_response
    # Loop should have made 2 provider calls (tool call + final response)
    assert provider.complete.call_count == 2


# ---------------------------------------------------------------------------
# Concurrency test (Task 4.12)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_concurrent_requests_independent_sessions() -> None:
    """Multiple concurrent requests to the ASGI server complete without interference."""
    responses = [f"Response {i}" for i in range(5)]

    entity = _make_entity("placeholder")
    app = create_conversation_app(entity)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async def one_request(i: int) -> dict[str, Any]:
            entity._loop.run.return_value = responses[i]
            resp = await client.post(
                "/conversation",
                json={"text": f"Request {i}", "conversation_id": f"session-{i}"},
            )
            assert resp.status_code == 200
            return resp.json()

        results = await asyncio.gather(*(one_request(i) for i in range(5)))

    assert len(results) == 5
    assert all(r["conversation_id"] == f"session-{i}" for i, r in enumerate(results))


# ---------------------------------------------------------------------------
# Latency smoke test (Task 4.12)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_conversation_latency_within_budget() -> None:
    """Response completes within 1 second for a single turn with a no-op loop.

    This is a sanity check on the framework overhead, not on LLM latency.
    """
    entity = _make_entity("Fast response")
    app = create_conversation_app(entity)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = time.monotonic()
        resp = await client.post("/conversation", json={"text": "Are you there?"})
        elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 1.0, f"Response took {elapsed:.3f}s — expected < 1s for mock loop"
