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
import uuid
from dataclasses import dataclass, field
from typing import Any

from chatterbox.conversation.loop import AgenticLoop, ToolDispatcher
from chatterbox.conversation.providers import (
    LLMAPIError,
    LLMConnectionError,
    LLMProvider,
    LLMRateLimitError,
    ToolDefinition,
)

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
        max_history_turns: int = 20,
        auto_create_conversation_id: bool = False,
    ) -> None:
        """Initialise the conversation entity.

        Args:
            provider: The LLM backend.
            tool_dispatcher: Async callable that executes tool calls.
            tools: Tool definitions available to the LLM.
            system_prompt: Persona/instruction text prepended to every turn.
            max_iterations: Max LLM calls per turn (passed to AgenticLoop).
            name: Display name shown in HA's Assist dashboard.
            max_history_turns: Maximum number of *conversation turns* (user +
                assistant pairs) to retain in memory. Older turns are silently
                dropped to bound token consumption. Defaults to 20 turns
                (40 messages). Set to ``0`` to disable truncation.
            auto_create_conversation_id: When ``True`` and the caller provides
                no ``conversation_id``, a new UUID4 session ID is generated and
                returned in the result. Useful for callers that do not manage
                their own IDs. Defaults to ``False`` (stateless single-turn
                behaviour).
        """
        self.name = name
        self.tools = tools or []
        self.max_history_turns = max_history_turns
        self.auto_create_conversation_id = auto_create_conversation_id
        self._loop = AgenticLoop(
            provider=provider,
            tool_dispatcher=tool_dispatcher,
            max_iterations=max_iterations,
            system_prompt=system_prompt,
        )
        # In-memory chat history per conversation_id.
        # Task 4.8 decision: persistent storage deferred to Epic 5.
        # See docs/context-management-research.md for rationale.
        self._histories: dict[str, list[dict[str, Any]]] = {}

    def _truncate_history(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return a window of *history* capped at ``max_history_turns``.

        Each turn is two messages (user + assistant). If ``max_history_turns``
        is 0 (disabled), the full history is returned unchanged.

        Args:
            history: Full in-memory message list for a session.

        Returns:
            A (possibly shortened) copy of the history.
        """
        if self.max_history_turns == 0 or len(history) == 0:
            return list(history)
        # Each turn = 2 messages; keep only the last N turns.
        keep = self.max_history_turns * 2
        if len(history) > keep:
            dropped = (len(history) - keep) // 2
            logger.debug(
                "History window: dropping %d oldest turn(s) to stay within "
                "max_history_turns=%d",
                dropped,
                self.max_history_turns,
            )
            return history[-keep:]
        return list(history)

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Process one conversation turn.

        Retrieves the chat history for the session (if any), runs the
        agentic loop, appends the new turn to history, and returns the
        LLM's response.

        If ``auto_create_conversation_id`` is ``True`` and no
        ``conversation_id`` is supplied, a new UUID4 session ID is created
        and returned in the result so the caller can track the session.

        Args:
            user_input: The user's transcribed utterance and session context.

        Returns:
            A `ConversationResult` with the LLM's text response.
        """
        conv_id = user_input.conversation_id
        if conv_id is None and self.auto_create_conversation_id:
            conv_id = str(uuid.uuid4())
            logger.debug("Auto-created conversation_id=%r", conv_id)

        history = self._histories.get(conv_id, []) if conv_id else []
        history = self._truncate_history(history)

        logger.info(
            "Processing conversation turn: id=%r, text=%r, history_len=%d",
            conv_id,
            user_input.text,
            len(history),
        )

        try:
            response_text = await self._loop.run(
                user_text=user_input.text,
                chat_history=history,
                tools=self.tools,
            )
        except RuntimeError as exc:
            logger.error(
                "AgenticLoop exceeded iteration limit for conversation id=%r: %s",
                conv_id,
                exc,
            )
            return ConversationResult(
                response_text=(
                    "I'm sorry, I got stuck trying to answer that. Please try again."
                ),
                conversation_id=conv_id,
            )
        except LLMRateLimitError as exc:
            logger.warning(
                "LLM rate limit hit for conversation id=%r: %s",
                conv_id,
                exc,
            )
            return ConversationResult(
                response_text=(
                    "I'm sorry, I'm receiving too many requests right now. "
                    "Please try again in a moment."
                ),
                conversation_id=conv_id,
            )
        except LLMConnectionError as exc:
            logger.error(
                "LLM connection error for conversation id=%r: %s",
                conv_id,
                exc,
            )
            return ConversationResult(
                response_text=(
                    "I'm sorry, I can't reach my language model right now. "
                    "Please check the connection and try again."
                ),
                conversation_id=conv_id,
            )
        except LLMAPIError as exc:
            logger.error(
                "LLM API error for conversation id=%r (status=%s): %s",
                conv_id,
                exc.status_code,
                exc,
            )
            return ConversationResult(
                response_text=(
                    "I'm sorry, my language model returned an error. Please try again."
                ),
                conversation_id=conv_id,
            )
        except Exception as exc:
            logger.error(
                "Unexpected error in agentic loop for conversation id=%r: %s",
                conv_id,
                exc,
                exc_info=True,
            )
            return ConversationResult(
                response_text=("I'm sorry, I encountered an error. Please try again."),
                conversation_id=conv_id,
            )

        # Update in-memory history for this session (only on success)
        if conv_id is not None:
            updated_history = list(history)
            updated_history.append({"role": "user", "content": user_input.text})
            updated_history.append({"role": "assistant", "content": response_text})
            self._histories[conv_id] = updated_history

        logger.info(
            "Conversation turn complete: id=%r, response=%r", conv_id, response_text
        )

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
