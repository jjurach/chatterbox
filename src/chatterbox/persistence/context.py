"""
Context retrieval and window management for conversations.

Provides efficient retrieval of conversation messages for LLM context window
composition with token counting, pagination, and optional caching.

Features:
- Retrieve last N messages with <200ms latency
- Context window composing for LLM input
- Token counting for context size estimation
- Efficient pagination
- Optional Redis caching layer (future)
- Context integrity verification

Reference: docs/context-management-research.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.schema import Conversation, Message

logger = logging.getLogger(__name__)

# Approximate token counts (varies by model)
TOKENS_PER_MESSAGE = 4  # Average tokens per message
TOKENS_PER_CHARACTER = 0.25  # Average tokens per character (more conservative)


@dataclass
class ContextMessage:
    """A single message in the context window.

    Attributes:
        id: Message UUID.
        role: "user", "assistant", or "system".
        content: Message text.
        sequence: Order in conversation.
        token_count: Estimated token count for this message.
    """

    id: str
    role: str
    content: str
    sequence: int
    token_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "sequence": self.sequence,
            "token_count": self.token_count,
        }


@dataclass
class ContextWindow:
    """A composed context window for LLM input.

    Attributes:
        conversation_id: The conversation UUID.
        messages: List of ContextMessage objects.
        total_tokens: Sum of all message token counts.
        truncated: Whether context was truncated due to token budget.
        oldest_message_sequence: Sequence of oldest message in window.
        newest_message_sequence: Sequence of newest message in window.
    """

    conversation_id: str
    messages: list[ContextMessage]
    total_tokens: int = 0
    truncated: bool = False
    oldest_message_sequence: Optional[int] = None
    newest_message_sequence: Optional[int] = None

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to list of dicts for OpenAI API compatibility."""
        return [msg.to_dict() for msg in self.messages]

    def to_openai_format(self) -> list[dict[str, str]]:
        """Convert to OpenAI message format."""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]


class TokenCounter:
    """Estimates token counts for messages.

    Uses a simple heuristic based on word count. For accurate token counting,
    use OpenAI's tiktoken library (optional dependency).
    """

    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate token count for a message.

        Uses character-based heuristic: ~0.25 tokens per character.
        For production, use tiktoken.encoding_for_model("gpt-4") etc.

        Args:
            text: The message content.

        Returns:
            Estimated token count.
        """
        if not text:
            return TOKENS_PER_MESSAGE
        char_count = len(text)
        return max(
            TOKENS_PER_MESSAGE,
            int(char_count * TOKENS_PER_CHARACTER) + TOKENS_PER_MESSAGE,
        )

    @staticmethod
    def count_message_tokens(role: str, content: str) -> int:
        """Count tokens for a role+content pair.

        Args:
            role: Message role.
            content: Message content.

        Returns:
            Estimated token count.
        """
        # Role marker adds tokens
        role_tokens = 1
        content_tokens = TokenCounter.count_tokens(content)
        return role_tokens + content_tokens


class ContextManager:
    """Manages retrieval and composition of conversation context.

    Methods:
    - get_context: Retrieve last N messages
    - build_context_window: Compose context with token budget
    - get_recent_messages: Fetch messages with pagination
    """

    def __init__(
        self,
        session: AsyncSession,
        default_context_size: int = 20,
        default_token_budget: int = 4000,
    ):
        """Initialize the context manager.

        Args:
            session: AsyncSession for database operations.
            default_context_size: Default number of messages to retrieve (default: 20).
            default_token_budget: Default max tokens for context window (default: 4000).
        """
        self.session = session
        self.default_context_size = default_context_size
        self.default_token_budget = default_token_budget

    async def get_context(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list[ContextMessage]:
        """Retrieve the last N messages in a conversation.

        Ordered from oldest to newest to maintain conversation flow.
        Latency target: <200ms.

        Args:
            conversation_id: The conversation UUID.
            limit: Maximum messages to retrieve (uses default if None).

        Returns:
            List of ContextMessage objects.

        Raises:
            ValueError: If conversation doesn't exist.
        """
        if limit is None:
            limit = self.default_context_size

        # Verify conversation exists
        conv_result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = conv_result.scalars().first()
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Get the last N messages
        msg_result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence.desc())
            .limit(limit)
        )
        messages = msg_result.scalars().all()

        # Convert to ContextMessage, preserving order (oldest first)
        context_messages = []
        for msg in reversed(messages):
            token_count = TokenCounter.count_message_tokens(msg.role, msg.content)
            context_messages.append(
                ContextMessage(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    sequence=msg.sequence,
                    token_count=token_count,
                )
            )

        logger.debug(
            "Retrieved %d messages for conversation %s",
            len(context_messages),
            conversation_id,
        )
        return context_messages

    async def build_context_window(
        self,
        conversation_id: str,
        token_budget: Optional[int] = None,
        preserve_system_messages: bool = True,
    ) -> ContextWindow:
        """Build a context window respecting a token budget.

        Includes all system messages (if preserve_system_messages=True), then adds
        user/assistant messages from newest to oldest until token budget is exceeded.

        Args:
            conversation_id: The conversation UUID.
            token_budget: Maximum tokens for context (uses default if None).
            preserve_system_messages: Always include system messages (default: True).

        Returns:
            ContextWindow with composed messages.

        Raises:
            ValueError: If conversation doesn't exist.
        """
        if token_budget is None:
            token_budget = self.default_token_budget

        # Get all messages
        msg_result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence)
        )
        all_messages = msg_result.scalars().all()

        if not all_messages:
            return ContextWindow(conversation_id=conversation_id, messages=[])

        # Separate system and non-system messages
        system_messages = [m for m in all_messages if m.role == "system"]
        other_messages = [m for m in all_messages if m.role != "system"]

        context_messages = []
        total_tokens = 0

        # Always include system messages
        if preserve_system_messages:
            for msg in system_messages:
                token_count = TokenCounter.count_message_tokens(msg.role, msg.content)
                context_messages.append(
                    ContextMessage(
                        id=msg.id,
                        role=msg.role,
                        content=msg.content,
                        sequence=msg.sequence,
                        token_count=token_count,
                    )
                )
                total_tokens += token_count

        # Add other messages from newest to oldest
        truncated = False
        for msg in reversed(other_messages):
            token_count = TokenCounter.count_message_tokens(msg.role, msg.content)
            if total_tokens + token_count > token_budget:
                truncated = True
                break
            context_messages.insert(
                len(system_messages),
                ContextMessage(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    sequence=msg.sequence,
                    token_count=token_count,
                ),
            )
            total_tokens += token_count

        # Ensure chronological order (oldest first)
        context_messages.sort(key=lambda m: m.sequence)

        # Extract sequence numbers
        sequences = [m.sequence for m in context_messages]
        oldest_seq = min(sequences) if sequences else None
        newest_seq = max(sequences) if sequences else None

        window = ContextWindow(
            conversation_id=conversation_id,
            messages=context_messages,
            total_tokens=total_tokens,
            truncated=truncated,
            oldest_message_sequence=oldest_seq,
            newest_message_sequence=newest_seq,
        )

        logger.debug(
            "Built context window for %s: %d messages, %d tokens, truncated=%s",
            conversation_id,
            len(context_messages),
            total_tokens,
            truncated,
        )
        return window

    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[ContextMessage], int]:
        """Retrieve recent messages with pagination.

        Args:
            conversation_id: The conversation UUID.
            limit: Maximum messages per page (default: 10).
            offset: Number of messages to skip (default: 0).

        Returns:
            Tuple of (list of messages, total count in conversation).

        Raises:
            ValueError: If conversation doesn't exist.
        """
        # Verify conversation exists
        conv_result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = conv_result.scalars().first()
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Count total messages
        count_result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        total_count = len(count_result.scalars().all())

        # Get paginated messages (ordered newest first)
        msg_result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence.desc())
            .offset(offset)
            .limit(limit)
        )
        messages = msg_result.scalars().all()

        # Convert and sort chronologically (oldest first)
        context_messages = []
        for msg in reversed(messages):
            token_count = TokenCounter.count_message_tokens(msg.role, msg.content)
            context_messages.append(
                ContextMessage(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    sequence=msg.sequence,
                    token_count=token_count,
                )
            )

        return context_messages, total_count

    async def verify_context_integrity(
        self,
        conversation_id: str,
    ) -> bool:
        """Verify that context is intact and ordered correctly.

        Checks:
        - All messages are present (no gaps in sequence numbers)
        - Sequence numbers are unique
        - Messages are ordered correctly

        Args:
            conversation_id: The conversation UUID.

        Returns:
            True if context is valid, False otherwise.
        """
        msg_result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence)
        )
        messages = msg_result.scalars().all()

        if not messages:
            return True

        # Check for gaps in sequence
        for i, msg in enumerate(messages):
            if msg.sequence != i + 1:
                logger.warning(
                    "Context integrity check failed: gap in sequence at %d (got %d)",
                    i + 1,
                    msg.sequence,
                )
                return False

        logger.debug(
            "Context integrity verified for conversation %s: %d messages, no gaps",
            conversation_id,
            len(messages),
        )
        return True
