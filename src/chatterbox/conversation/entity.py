"""
ChatterboxConversationEntity — HA ConversationEntity skeleton.

This module defines the dataclasses and entity class that mirror the Home
Assistant ``ConversationEntity`` interface. It deliberately does NOT import
from `homeassistant` so that it can be unit-tested without a running HA
instance.

When integrating with HA (Epic 4.11 — Implement Custom HA Conversation Entity),
this skeleton will be subclassed or adapted to extend the real
``homeassistant.components.conversation.ConversationEntity``.

Reference: https://developers.home-assistant.io/docs/core/conversation/custom_agent/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from chatterbox.conversation.loop import AgenticLoop, ToolDispatcher
from chatterbox.conversation.providers import LLMProvider, ToolDefinition

logger = logging.getLogger(__name__)

# System prompt template for the voice assistant persona.
_DEFAULT_SYSTEM_PROMPT = (
    "You are Chatterbox, a helpful voice assistant integrated with Home Assistant. "
    "Answer concisely — responses are spoken aloud via text-to-speech. "
    "Use the available tools to look up real-time information when needed. "
    "Do not make up information; if you don't know, say so."
)


@dataclass
class ConversationInput:
    """Input to a single conversation turn.

    Mirrors ``homeassistant.components.conversation.ConversationInput``.

    Attributes:
        text: The user's transcribed utterance.
        conversation_id: Optional session ID for multi-turn context.
        language: BCP-47 language tag (e.g. ``"en"``).
    """

    text: str
    conversation_id: str | None = None
    language: str = "en"


@dataclass
class ConversationResult:
    """Result of a single conversation turn.

    Mirrors ``homeassistant.components.conversation.ConversationResult``.

    Attributes:
        response_text: The text response to be spoken via TTS.
        conversation_id: Session ID (echoed back for multi-turn tracking).
        extra: Optional dict for metadata (latency, model, tool calls used, etc.).
    """

    response_text: str
    conversation_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ChatterboxConversationEntity:
    """Voice assistant ConversationEntity backed by the AgenticLoop.

    This class connects the HA ConversationEntity interface to the
    `AgenticLoop`. It owns the loop instance and manages per-session chat
    history (in-memory; sessions are keyed by ``conversation_id``).

    In Epic 4.11, this will be extended to subclass HA's actual
    ``ConversationEntity`` base class and register as an HA integration.

    Attributes:
        name: Display name shown in HA's Assist dashboard.
        loop: The `AgenticLoop` instance.
        tools: Tool definitions available to the LLM.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_dispatcher: ToolDispatcher,
        tools: list[ToolDefinition] | None = None,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
        max_iterations: int = 10,
        name: str = "Chatterbox",
    ) -> None:
        self.name = name
        self.tools = tools or []
        self._loop = AgenticLoop(
            provider=provider,
            tool_dispatcher=tool_dispatcher,
            max_iterations=max_iterations,
            system_prompt=system_prompt,
        )
        # In-memory chat history per conversation_id.
        # This is a stub — Epic 4.8/4.9 will evaluate persistent storage.
        self._histories: dict[str, list[dict[str, Any]]] = {}

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Process one conversation turn.

        Retrieves the chat history for the session (if any), runs the
        agentic loop, appends the new turn to history, and returns the
        LLM's response.

        Args:
            user_input: The user's transcribed utterance and session context.

        Returns:
            A `ConversationResult` with the LLM's text response.
        """
        conv_id = user_input.conversation_id
        history = self._histories.get(conv_id, []) if conv_id else []

        logger.info(
            "Processing conversation turn: id=%r, text=%r, history_len=%d",
            conv_id,
            user_input.text,
            len(history),
        )

        response_text = await self._loop.run(
            user_text=user_input.text,
            chat_history=history,
            tools=self.tools,
        )

        # Update in-memory history for this session
        if conv_id is not None:
            updated_history = list(history)
            updated_history.append({"role": "user", "content": user_input.text})
            updated_history.append({"role": "assistant", "content": response_text})
            self._histories[conv_id] = updated_history

        logger.info("Conversation turn complete: id=%r, response=%r", conv_id, response_text)

        return ConversationResult(
            response_text=response_text,
            conversation_id=conv_id,
        )

    def clear_history(self, conversation_id: str) -> None:
        """Clear the chat history for a session.

        Args:
            conversation_id: The session to clear.
        """
        self._histories.pop(conversation_id, None)

    def clear_all_history(self) -> None:
        """Clear all in-memory chat histories."""
        self._histories.clear()
