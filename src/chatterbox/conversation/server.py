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
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from chatterbox.conversation.entity import (
    ChatterboxConversationEntity,
    ConversationInput,
)

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
# App factory
# ---------------------------------------------------------------------------


def create_conversation_app(entity: ChatterboxConversationEntity) -> FastAPI:
    """Create a FastAPI application wrapping *entity*.

    Args:
        entity: A fully initialised ``ChatterboxConversationEntity``.  The
            caller is responsible for building the provider, tools, and
            dispatcher before passing the entity in.

    Returns:
        A configured ``FastAPI`` application ready to be served or used in
        tests via ``httpx.AsyncClient(app=app, ...)``.
    """
    app = FastAPI(
        title="Chatterbox Conversation API",
        description=(
            "REST interface for the Chatterbox agentic conversation loop. "
            "Bridges Wyoming STT output → LLM → Wyoming TTS input without "
            "requiring a running Home Assistant instance."
        ),
        version="0.1.0",
    )

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
