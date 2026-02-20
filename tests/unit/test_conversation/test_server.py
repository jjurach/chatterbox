"""Unit tests for chatterbox.conversation.server.

Tests use httpx.AsyncClient against the ASGI app (no real HTTP server).
The ChatterboxConversationEntity is wired with a mocked AgenticLoop so
no real LLM is needed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from chatterbox.conversation.entity import ChatterboxConversationEntity
from chatterbox.conversation.providers import (
    LLMAPIError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMProvider,
)
from chatterbox.conversation.server import create_conversation_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(loop_response: str = "Default response") -> ChatterboxConversationEntity:
    """Return an entity with a mocked AgenticLoop."""
    provider = AsyncMock(spec=LLMProvider)

    async def noop_dispatcher(name: str, args: dict[str, Any]) -> str:
        return "tool_result"

    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=noop_dispatcher,
        auto_create_conversation_id=False,
    )
    entity._loop.run = AsyncMock(return_value=loop_response)
    return entity


async def _client(entity: ChatterboxConversationEntity) -> AsyncClient:
    """Return an AsyncClient bound to the app for *entity*."""
    app = create_conversation_app(entity)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_ok() -> None:
    entity = _make_entity()
    async with await _client(entity) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["entity_name"] == "Chatterbox"
    assert body["active_sessions"] == 0


@pytest.mark.anyio
async def test_health_shows_active_sessions() -> None:
    entity = _make_entity("hi")
    # Manually insert a session
    entity._histories["sess-1"] = [{"role": "user", "content": "hi"}]
    async with await _client(entity) as client:
        resp = await client.get("/health")
    assert resp.json()["active_sessions"] == 1


# ---------------------------------------------------------------------------
# POST /conversation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_conversation_returns_response_text() -> None:
    entity = _make_entity("The weather is sunny.")
    async with await _client(entity) as client:
        resp = await client.post("/conversation", json={"text": "What is the weather?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_text"] == "The weather is sunny."


@pytest.mark.anyio
async def test_post_conversation_echoes_conversation_id() -> None:
    entity = _make_entity("Response")
    async with await _client(entity) as client:
        resp = await client.post(
            "/conversation",
            json={"text": "Hello", "conversation_id": "sess-abc"},
        )
    assert resp.status_code == 200
    assert resp.json()["conversation_id"] == "sess-abc"


@pytest.mark.anyio
async def test_post_conversation_none_id_when_not_provided() -> None:
    entity = _make_entity("OK")
    async with await _client(entity) as client:
        resp = await client.post("/conversation", json={"text": "Hi"})
    assert resp.status_code == 200
    assert resp.json()["conversation_id"] is None


@pytest.mark.anyio
async def test_post_conversation_passes_text_to_entity() -> None:
    entity = _make_entity("Got it")
    async with await _client(entity) as client:
        await client.post("/conversation", json={"text": "Tell me a joke"})
    entity._loop.run.assert_called_once()
    call_kwargs = entity._loop.run.call_args
    user_text = call_kwargs.kwargs.get("user_text") or call_kwargs.args[0]
    assert user_text == "Tell me a joke"


@pytest.mark.anyio
async def test_post_conversation_missing_text_returns_422() -> None:
    entity = _make_entity()
    async with await _client(entity) as client:
        resp = await client.post("/conversation", json={})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_post_conversation_rate_limit_returns_fallback() -> None:
    entity = _make_entity()
    entity._loop.run = AsyncMock(side_effect=LLMRateLimitError("rate limited"))
    async with await _client(entity) as client:
        resp = await client.post("/conversation", json={"text": "Hi"})
    assert resp.status_code == 200
    body = resp.json()
    assert "too many requests" in body["response_text"].lower()


@pytest.mark.anyio
async def test_post_conversation_connection_error_returns_fallback() -> None:
    entity = _make_entity()
    entity._loop.run = AsyncMock(side_effect=LLMConnectionError("unreachable"))
    async with await _client(entity) as client:
        resp = await client.post("/conversation", json={"text": "Hi"})
    assert resp.status_code == 200
    body = resp.json()
    assert "can't reach" in body["response_text"].lower()


@pytest.mark.anyio
async def test_post_conversation_api_error_returns_fallback() -> None:
    entity = _make_entity()
    entity._loop.run = AsyncMock(side_effect=LLMAPIError("bad response", status_code=500))
    async with await _client(entity) as client:
        resp = await client.post("/conversation", json={"text": "Hi"})
    assert resp.status_code == 200
    body = resp.json()
    assert "error" in body["response_text"].lower()


@pytest.mark.anyio
async def test_post_conversation_extra_defaults_empty() -> None:
    entity = _make_entity("Response")
    async with await _client(entity) as client:
        resp = await client.post("/conversation", json={"text": "Hi"})
    assert resp.json()["extra"] == {}


# ---------------------------------------------------------------------------
# Multi-turn conversation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_conversation_multi_turn_history_grows() -> None:
    entity = _make_entity("Turn 2 response")
    async with await _client(entity) as client:
        await client.post(
            "/conversation",
            json={"text": "First turn", "conversation_id": "sess-1"},
        )
        entity._loop.run.return_value = "Turn 2 response"
        resp2 = await client.post(
            "/conversation",
            json={"text": "Second turn", "conversation_id": "sess-1"},
        )
    assert resp2.status_code == 200
    assert resp2.json()["response_text"] == "Turn 2 response"
    # Two turns stored: 2 messages per turn
    assert len(entity._histories["sess-1"]) == 4


# ---------------------------------------------------------------------------
# DELETE /conversation/{id}
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_session_clears_history() -> None:
    entity = _make_entity("Hi")
    entity._histories["sess-del"] = [{"role": "user", "content": "hello"}]
    async with await _client(entity) as client:
        resp = await client.delete("/conversation/sess-del")
    assert resp.status_code == 204
    assert "sess-del" not in entity._histories


@pytest.mark.anyio
async def test_delete_nonexistent_session_is_idempotent() -> None:
    entity = _make_entity()
    async with await _client(entity) as client:
        resp = await client.delete("/conversation/no-such-id")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# DELETE /conversation (all sessions)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_all_sessions() -> None:
    entity = _make_entity()
    entity._histories["a"] = []
    entity._histories["b"] = []
    async with await _client(entity) as client:
        resp = await client.delete("/conversation")
    assert resp.status_code == 204
    assert entity._histories == {}
