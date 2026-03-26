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

# For Zeroconf lifespan tests
AsyncClient = AsyncClient  # Re-export for clarity in test_health_endpoint_with_zeroconf


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


async def _client(
    entity: ChatterboxConversationEntity, api_key: str = ""
) -> AsyncClient:
    """Return an AsyncClient bound to the app for *entity*.

    For backward compatibility with existing tests, if api_key is not specified,
    we disable authentication by passing api_key="" to the app factory.
    This allows old tests to work without modification.

    Args:
        entity: The conversation entity.
        api_key: Optional API key for authentication. Empty string "" (default) disables auth
                 for backward compatibility. Pass a non-empty string to enable auth with that key.
    """
    app = create_conversation_app(entity, api_key=api_key, enable_zeroconf=False)
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


# ---------------------------------------------------------------------------
# Zeroconf integration tests
# ---------------------------------------------------------------------------


def test_create_conversation_app_with_zeroconf_disabled() -> None:
    """Test that create_conversation_app works with zeroconf disabled."""
    from chatterbox.conversation.server import create_conversation_app

    entity = _make_entity()
    app = create_conversation_app(entity, enable_zeroconf=False)
    assert app is not None


def test_create_conversation_app_with_zeroconf_enabled() -> None:
    """Test that create_conversation_app initializes with zeroconf enabled."""
    from unittest.mock import patch
    from chatterbox.conversation.server import create_conversation_app

    entity = _make_entity()
    with patch("chatterbox.conversation.server.ChatterboxZeroconf") as mock_zc:
        app = create_conversation_app(entity, port=8765, enable_zeroconf=True)
        assert app is not None
        # Zeroconf should be instantiated but not started until lifespan
        mock_zc.assert_called_once_with(port=8765, version="0.1.0")


@pytest.mark.anyio
async def test_create_conversation_app_lifespan_startup_success() -> None:
    """Test that lifespan startup calls zeroconf.start()."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from chatterbox.conversation.server import create_conversation_app

    entity = _make_entity()
    with patch("chatterbox.conversation.server.ChatterboxZeroconf") as mock_zc_class:
        mock_zc = MagicMock()
        mock_zc_class.return_value = mock_zc

        app = create_conversation_app(entity, port=8765, enable_zeroconf=True)

        # Simulate app startup
        async with app.router.lifespan_context(app):
            # Zeroconf.start should have been called
            mock_zc.start.assert_called_once()


@pytest.mark.anyio
async def test_create_conversation_app_lifespan_shutdown_success() -> None:
    """Test that lifespan shutdown calls zeroconf.stop()."""
    from unittest.mock import MagicMock, patch
    from chatterbox.conversation.server import create_conversation_app

    entity = _make_entity()
    with patch("chatterbox.conversation.server.ChatterboxZeroconf") as mock_zc_class:
        mock_zc = MagicMock()
        mock_zc_class.return_value = mock_zc

        app = create_conversation_app(entity, port=8765, enable_zeroconf=True)

        # Simulate app startup and shutdown
        async with app.router.lifespan_context(app):
            pass  # Exit the context (triggers shutdown)

        # Zeroconf.stop should have been called
        mock_zc.stop.assert_called_once()


@pytest.mark.anyio
async def test_create_conversation_app_lifespan_startup_error_handling() -> None:
    """Test that lifespan continues even if zeroconf.start() fails."""
    from unittest.mock import MagicMock, patch
    from chatterbox.conversation.server import create_conversation_app

    entity = _make_entity()
    with patch("chatterbox.conversation.server.ChatterboxZeroconf") as mock_zc_class:
        mock_zc = MagicMock()
        mock_zc.start.side_effect = Exception("Zeroconf start failed")
        mock_zc_class.return_value = mock_zc

        app = create_conversation_app(entity, port=8765, enable_zeroconf=True)

        # Should not raise, even though zeroconf.start() failed
        async with app.router.lifespan_context(app):
            pass  # Should complete without error


@pytest.mark.anyio
async def test_health_endpoint_with_zeroconf() -> None:
    """Test that health endpoint still works with zeroconf enabled."""
    from unittest.mock import patch
    from chatterbox.conversation.server import create_conversation_app

    entity = _make_entity()
    with patch("chatterbox.conversation.server.ChatterboxZeroconf"):
        app = create_conversation_app(entity, port=8765, enable_zeroconf=True)
        async with await _client(entity) as client:
            # Temporarily replace the client with one using the new app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_with_zc:
                resp = await client_with_zc.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Bearer Token Authentication
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_endpoint_no_auth_required() -> None:
    """Test that GET /health does not require authentication."""
    entity = _make_entity()
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_post_conversation_with_valid_bearer_token() -> None:
    """Test that POST /conversation accepts valid Bearer token."""
    entity = _make_entity("OK")
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/conversation",
            json={"text": "Hello"},
            headers={"Authorization": "Bearer secret-key"},
        )
    assert resp.status_code == 200
    assert resp.json()["response_text"] == "OK"


@pytest.mark.anyio
async def test_post_conversation_with_invalid_bearer_token() -> None:
    """Test that POST /conversation rejects invalid Bearer token."""
    entity = _make_entity()
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/conversation",
            json={"text": "Hello"},
            headers={"Authorization": "Bearer wrong-key"},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert "detail" in body
    assert "Invalid authentication credentials" in body["detail"]


@pytest.mark.anyio
async def test_post_conversation_missing_auth_header() -> None:
    """Test that POST /conversation rejects request without Authorization header."""
    entity = _make_entity()
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/conversation",
            json={"text": "Hello"},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert "detail" in body
    assert "Missing or invalid Authorization header" in body["detail"]


@pytest.mark.anyio
async def test_post_conversation_malformed_bearer_header() -> None:
    """Test that POST /conversation rejects malformed Authorization header."""
    entity = _make_entity()
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/conversation",
            json={"text": "Hello"},
            headers={"Authorization": "NotBearer secret-key"},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert "Missing or invalid Authorization header" in body["detail"]


@pytest.mark.anyio
async def test_delete_conversation_requires_auth() -> None:
    """Test that DELETE /conversation/{id} requires valid Bearer token."""
    entity = _make_entity()
    entity._histories["sess-1"] = [{"role": "user", "content": "hello"}]
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Without auth
        resp = await client.delete("/conversation/sess-1")
        assert resp.status_code == 401

        # With valid auth
        resp = await client.delete(
            "/conversation/sess-1",
            headers={"Authorization": "Bearer secret-key"},
        )
        assert resp.status_code == 204


@pytest.mark.anyio
async def test_delete_all_conversations_requires_auth() -> None:
    """Test that DELETE /conversation requires valid Bearer token."""
    entity = _make_entity()
    entity._histories["a"] = []
    entity._histories["b"] = []
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Without auth
        resp = await client.delete("/conversation")
        assert resp.status_code == 401

        # With valid auth
        resp = await client.delete(
            "/conversation",
            headers={"Authorization": "Bearer secret-key"},
        )
        assert resp.status_code == 204
        assert entity._histories == {}


@pytest.mark.anyio
async def test_bearer_token_case_sensitive() -> None:
    """Test that Bearer token is case-sensitive."""
    entity = _make_entity()
    app = create_conversation_app(entity, api_key="MySecretKey123", enable_zeroconf=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Wrong case should fail
        resp = await client.post(
            "/conversation",
            json={"text": "Hello"},
            headers={"Authorization": "Bearer mysecretkey123"},
        )
        assert resp.status_code == 401

        # Correct case should succeed
        resp = await client.post(
            "/conversation",
            json={"text": "Hello"},
            headers={"Authorization": "Bearer MySecretKey123"},
        )
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_empty_bearer_token() -> None:
    """Test that empty Bearer token is rejected."""
    entity = _make_entity()
    app = create_conversation_app(entity, api_key="secret-key", enable_zeroconf=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/conversation",
            json={"text": "Hello"},
            headers={"Authorization": "Bearer "},
        )
    assert resp.status_code == 401
    assert "Invalid authentication credentials" in resp.json()["detail"]
