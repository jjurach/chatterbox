"""
HTTP server for ChatterboxConversationEntity.

Exposes the conversation entity over a simple REST API so that the
agentic loop can be exercised without a running Home Assistant instance.
This is the integration point between the Wyoming STT/TTS pipeline and
the conversation layer during development and testing.

In production, the conversation entity will be wired directly into HA via
the ``ConversationEntity`` subclass pattern (Task 4.11 / Epic 4.1 research).

Endpoints
---------
POST   /conversation             Process one conversation turn.
DELETE /conversation/{id}        Clear history for a session.
DELETE /conversation             Clear all session histories.
GET    /health                   Health / readiness check.

Usage (standalone)::

    from chatterbox.conversation.server import create_conversation_app
    from chatterbox.conversation.entity import ChatterboxConversationEntity
    from chatterbox.conversation.providers import OpenAICompatibleProvider
    from chatterbox.conversation.tools.registry import ToolRegistry
    from chatterbox.conversation.tools.weather import WeatherTool
    from chatterbox.conversation.tools.datetime_tool import DateTimeTool
    import uvicorn

    registry = ToolRegistry()
    registry.register(WeatherTool.TOOL_DEFINITION, WeatherTool().as_dispatcher_entry())
    registry.register(DateTimeTool.TOOL_DEFINITION, DateTimeTool().as_dispatcher_entry())

    provider = OpenAICompatibleProvider(model="gpt-4o-mini")
    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=registry.build_dispatcher(),
        tools=registry.get_definitions(),
    )
    app = create_conversation_app(entity)
    uvicorn.run(app, host="0.0.0.0", port=8765)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from chatterbox.config import get_settings
from chatterbox.conversation.entity import (
    ChatterboxConversationEntity,
    ConversationInput,
)
from chatterbox.conversation.zeroconf import ChatterboxZeroconf

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ConversationRequest(BaseModel):
    """Body for POST /conversation."""

    text: str = Field(..., description="Transcribed user utterance.")
    conversation_id: str | None = Field(
        default=None,
        description="Session ID for multi-turn context. Omit for single-turn.",
    )
    language: str = Field(
        default="en",
        description="BCP-47 language tag for the utterance.",
    )


class ConversationResponse(BaseModel):
    """Response body for POST /conversation."""

    response_text: str = Field(..., description="LLM response to be spoken via TTS.")
    conversation_id: str | None = Field(
        default=None,
        description="Session ID (echoed or newly created for multi-turn sessions).",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (latency, model, tool calls, etc.).",
    )


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    entity_name: str
    active_sessions: int


# ---------------------------------------------------------------------------
# Authentication middleware
# ---------------------------------------------------------------------------


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates Bearer token in Authorization header.

    All endpoints except GET /health require a valid Authorization header
    with format "Bearer <api_key>". The api_key is read from Settings.api_key.

    Returns:
        HTTP 401 with JSON error if token is missing or invalid.
    """

    # Sentinel value to distinguish "no api_key provided" from "empty string"
    _UNSET = object()

    def __init__(self, app: FastAPI, api_key: str | object = _UNSET) -> None:
        """Initialize middleware with optional API key override.

        Args:
            app: The FastAPI application instance.
            api_key: Optional API key for testing. If _UNSET (default), uses Settings.api_key.
                    If empty string (""), disables authentication.
        """
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Validate Bearer token for protected endpoints.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The response from the next handler, or a 401 JSON error.
        """
        # /health is always allowed
        if request.url.path == "/health" and request.method == "GET":
            return await call_next(request)

        # Get the API key (from init or Settings)
        api_key = self.api_key
        if api_key is self._UNSET:
            settings = get_settings()
            api_key = settings.api_key

        # If no API key is configured, skip authentication (useful for dev/test)
        if not api_key:
            return await call_next(request)

        # All other endpoints require Bearer token
        auth_header = request.headers.get("Authorization", "")

        # Validate Bearer token format and value
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication credentials"},
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_conversation_app(
    entity: ChatterboxConversationEntity,
    port: int = 8765,
    enable_zeroconf: bool = True,
    api_key: str | None = None,
) -> FastAPI:
    """Create a FastAPI application wrapping *entity*.

    Args:
        entity: A fully initialised ``ChatterboxConversationEntity``.  The
            caller is responsible for building the provider, tools, and
            dispatcher before passing the entity in.
        port: Port number for Zeroconf advertisement (default 8765).
        enable_zeroconf: Whether to advertise via Zeroconf/mDNS (default True).
        api_key: Optional API key for Bearer token authentication. If None,
            uses Settings.api_key. For testing only.

    Returns:
        A configured ``FastAPI`` application ready to be served or used in
        tests via ``httpx.AsyncClient(app=app, ...)``.
    """

    # Create Zeroconf instance if enabled
    zeroconf: ChatterboxZeroconf | None = None
    if enable_zeroconf:
        zeroconf = ChatterboxZeroconf(port=port, version="0.1.0")

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore
        """Manage application lifespan: startup and shutdown."""
        # Startup
        if zeroconf:
            try:
                zeroconf.start()
            except Exception as e:
                logger.error("Failed to start Zeroconf: %s", e)
                # Don't fail startup if Zeroconf fails (not critical)

        yield

        # Shutdown
        if zeroconf:
            try:
                zeroconf.stop()
            except Exception as e:
                logger.error("Error during Zeroconf shutdown: %s", e)

    app = FastAPI(
        title="Chatterbox Conversation API",
        description=(
            "REST interface for the Chatterbox agentic conversation loop. "
            "Bridges Wyoming STT output → LLM → Wyoming TTS input without "
            "requiring a running Home Assistant instance."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add Bearer token authentication middleware
    app.add_middleware(BearerTokenMiddleware, api_key=api_key)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Return server health and entity status."""
        return HealthResponse(
            status="ok",
            entity_name=entity.name,
            active_sessions=len(entity._histories),
        )

    @app.post("/conversation", response_model=ConversationResponse)
    async def process_conversation(body: ConversationRequest) -> ConversationResponse:
        """Process one conversation turn through the agentic loop.

        Accepts the transcribed utterance from the STT stage, runs it through
        the configured ``ChatterboxConversationEntity``, and returns the text
        response destined for the TTS stage.

        Args:
            body: The conversation request with user text and optional session ID.

        Returns:
            The LLM's text response and the echoed / newly assigned session ID.

        Raises:
            HTTPException 422: If the request body is malformed (FastAPI default).
            HTTPException 500: If an unexpected server error occurs.
        """
        logger.info(
            "POST /conversation: text=%r conversation_id=%r",
            body.text,
            body.conversation_id,
        )

        user_input = ConversationInput(
            text=body.text,
            conversation_id=body.conversation_id,
            language=body.language,
        )

        try:
            result = await entity.async_process(user_input)
        except Exception as exc:
            logger.error("Unexpected error in async_process: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error") from exc

        logger.info(
            "POST /conversation response: text=%r conversation_id=%r",
            result.response_text,
            result.conversation_id,
        )
        return ConversationResponse(
            response_text=result.response_text,
            conversation_id=result.conversation_id,
            extra=result.extra,
        )

    @app.delete("/conversation/{conversation_id}", status_code=204)
    async def clear_session(conversation_id: str) -> None:
        """Clear the chat history for a specific session.

        This frees the in-memory state for the given ``conversation_id``.
        Subsequent turns with the same ID will start fresh.

        Args:
            conversation_id: The session whose history should be cleared.
        """
        logger.info("DELETE /conversation/%s", conversation_id)
        entity.clear_history(conversation_id)

    @app.delete("/conversation", status_code=204)
    async def clear_all_sessions() -> None:
        """Clear all in-memory session histories."""
        logger.info("DELETE /conversation (all sessions)")
        entity.clear_all_history()

    return app
