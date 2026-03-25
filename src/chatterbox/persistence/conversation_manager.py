"""
ConversationManager: Integration point between Epic 4 LLM framework and persistent storage.

This module provides the ``ConversationManager`` class, which bridges the
``ChatterboxConversationEntity`` (from Epic 4) and the storage backend
(SQLiteStorage, etc. from Epic 5).

ConversationManager handles:
- Loading conversation history from storage
- Storing new messages after LLM processing
- Logging tool calls with metadata (arguments, results, duration)
- Token tracking for cost analysis
- Context snapshots for debugging and analytics

Designed for use by ChatterboxConversationEntity.async_process() to automatically
persist all conversation turns and tool interactions to the database.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.backends.base import StorageBackend
from chatterbox.persistence.repositories import (
    ConversationRepository,
    ContextSnapshotRepository,
    MessageRepository,
    ToolCallRepository,
)
from chatterbox.persistence.schema import Conversation, Message, ToolCall

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages persistent storage of conversations and related data.

    Acts as a bridge between the Epic 4 agentic loop (ChatterboxConversationEntity)
    and the Epic 5 persistence layer (StorageBackend and repositories).

    Responsibilities:
    - Load conversation history from storage for context
    - Store new messages after LLM response
    - Log tool calls with full metadata (arguments, results, duration)
    - Track token usage for cost analysis
    - Create context snapshots at strategic points

    Typical usage::

        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///chatterbox.db")
        manager = ConversationManager(storage)

        # Load history for context
        history = await manager.load_history(conversation_id, limit=20)

        # After LLM processes and returns response:
        await manager.store_message(
            conversation_id=conv_id,
            role="user",
            content=user_text,
        )
        await manager.store_message(
            conversation_id=conv_id,
            role="assistant",
            content=response_text,
            metadata={"model": "gpt-4", "tokens": 150},
        )

        # Log a tool call
        start_time = time.time()
        tool_result = await weather_tool.get_weather("London")
        duration_ms = int((time.time() - start_time) * 1000)

        await manager.log_tool_call(
            conversation_id=conv_id,
            call_id="call_123",
            tool_name="get_weather",
            arguments={"location": "London"},
            result=json.dumps(tool_result),
            duration_ms=duration_ms,
        )
    """

    def __init__(self, storage: StorageBackend) -> None:
        """Initialize the ConversationManager.

        Args:
            storage: A StorageBackend implementation (e.g., SQLiteStorage).
        """
        self.storage = storage
        logger.info("ConversationManager initialized with backend: %s", type(storage).__name__)

    async def initialize(self) -> None:
        """Initialize the storage backend.

        Must be called once during application startup before using any other
        methods. Safe to call multiple times.

        Raises:
            Exception: If initialization fails.
        """
        await self.storage.initialize()
        logger.info("ConversationManager storage initialized")

    async def shutdown(self) -> None:
        """Shut down the storage backend gracefully.

        Must be called during application shutdown. Safe to call multiple times
        and even if initialize() was never called.
        """
        await self.storage.shutdown()
        logger.info("ConversationManager storage shut down")

    async def load_history(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Load conversation history from storage for context.

        Loads all messages for a conversation (or the most recent N messages
        if ``limit`` is set). Messages are formatted as dict with "role" and
        "content" keys, suitable for passing to the LLM.

        Args:
            conversation_id: The conversation's UUID.
            limit: Maximum number of recent messages to return. ``None`` returns
                all messages. Default: ``None``.

        Returns:
            List of message dicts in order: ``{"role": "user" | "assistant" | "system", "content": "..."}``

        Raises:
            Exception: If database access fails.
        """
        async with self.storage.get_session() as session:
            msg_repo = MessageRepository(session)
            messages = await msg_repo.get_by_conversation(conversation_id, limit=limit)

        result = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        logger.debug(
            "Loaded conversation history: conversation_id=%r, messages=%d",
            conversation_id,
            len(result),
        )
        return result

    async def load_conversation(
        self, conversation_id: str
    ) -> Conversation | None:
        """Load a Conversation record from storage.

        Args:
            conversation_id: The conversation's UUID.

        Returns:
            The Conversation ORM object, or None if not found.

        Raises:
            Exception: If database access fails.
        """
        async with self.storage.get_session() as session:
            conv_repo = ConversationRepository(session)
            conversation = await conv_repo.get_by_id(conversation_id)
        return conversation

    async def create_conversation(
        self,
        user_id: str | None = None,
        conversation_id: str | None = None,
        language: str = "en",
        device: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation record.

        Args:
            user_id: Optional FK to User.id.
            conversation_id: Optional UUID string (auto-generated if not provided).
            language: BCP-47 language tag (default: "en").
            device: Optional device identifier.
            metadata: Optional JSON metadata.

        Returns:
            The created Conversation object.

        Raises:
            Exception: If database access or constraint violation occurs.
        """
        async with self.storage.get_session() as session:
            conv_repo = ConversationRepository(session)
            conversation = await conv_repo.create(
                user_id=user_id,
                conversation_id=conversation_id,
                language=language,
                device=device,
                metadata=metadata,
            )
            # Note: session auto-commits on context exit due to backend implementation
        logger.info(
            "Created conversation: id=%r, conversation_id=%r",
            conversation.id,
            conversation.conversation_id,
        )
        return conversation

    async def store_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Store a message in the conversation.

        Args:
            conversation_id: FK to Conversation.id.
            role: "user", "assistant", or "system".
            content: The message text.
            metadata: Optional JSON metadata (token count, latency, model, etc.).

        Returns:
            The created Message object.

        Raises:
            ValueError: If role is invalid.
            Exception: If database access fails.
        """
        async with self.storage.get_session() as session:
            msg_repo = MessageRepository(session)
            message = await msg_repo.add(
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata=metadata or {},
            )
        logger.debug(
            "Stored message: conversation_id=%r, role=%r, seq=%d",
            conversation_id,
            role,
            message.sequence,
        )
        return message

    async def log_tool_call(
        self,
        conversation_id: str,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        message_id: str | None = None,
        result: str | None = None,
        error: str | None = None,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ToolCall:
        """Log a tool invocation.

        Records both the LLM's request to invoke a tool and the result returned
        by the tool dispatcher. Used for auditing, debugging, cost analysis, and
        analytics.

        Args:
            conversation_id: FK to Conversation.id.
            call_id: Tool call ID from OpenAI (for correlation).
            tool_name: Name of the tool invoked (e.g., "get_weather").
            arguments: JSON dict of input arguments.
            message_id: Optional FK to Message.id (message containing tool_calls).
            result: Optional result string from the tool (typically JSON).
            error: Optional error message if tool execution failed.
            duration_ms: Optional execution time in milliseconds.
            metadata: Optional additional call metadata.

        Returns:
            The created ToolCall object.

        Raises:
            Exception: If database access fails.
        """
        async with self.storage.get_session() as session:
            tool_repo = ToolCallRepository(session)
            tool_call = await tool_repo.add(
                conversation_id=conversation_id,
                call_id=call_id,
                tool_name=tool_name,
                arguments=arguments,
                message_id=message_id,
                result=result,
                error=error,
                duration_ms=duration_ms,
            )
            # Attach additional metadata if provided
            if metadata:
                tool_call.call_metadata = metadata

        logger.debug(
            "Logged tool call: conversation_id=%r, tool=%r, call_id=%r, duration=%sms",
            conversation_id,
            tool_name,
            call_id,
            duration_ms or "unknown",
        )
        return tool_call

    async def create_context_snapshot(
        self,
        conversation_id: str,
        context_window: list[dict[str, Any]],
        message_sequence: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Create a context snapshot for debugging or analytics.

        Captures the state of the context window at a specific point in the
        conversation. Useful for understanding what context the LLM saw, or
        for replaying conversations.

        Args:
            conversation_id: FK to Conversation.id.
            context_window: The list of messages in the context at snapshot time.
            message_sequence: Optional message sequence number.
            metadata: Optional JSON metadata (reason, truncation_count, etc.).

        Returns:
            The created ContextSnapshot object.

        Raises:
            Exception: If database access fails.
        """
        async with self.storage.get_session() as session:
            snap_repo = ContextSnapshotRepository(session)
            snapshot = await snap_repo.create(
                conversation_id=conversation_id,
                context_window=context_window,
                message_sequence=message_sequence,
                metadata=metadata or {},
            )
        logger.debug(
            "Created context snapshot: conversation_id=%r, messages=%d",
            conversation_id,
            len(context_window),
        )
        return snapshot

    async def get_tool_calls(
        self, conversation_id: str, tool_name: str | None = None, limit: int = 100
    ) -> list[ToolCall]:
        """Retrieve tool calls from a conversation.

        Args:
            conversation_id: FK to Conversation.id.
            tool_name: Optional filter to return only calls to a specific tool.
            limit: Maximum number of results (default: 100).

        Returns:
            List of ToolCall objects, ordered by most recent first.

        Raises:
            Exception: If database access fails.
        """
        async with self.storage.get_session() as session:
            tool_repo = ToolCallRepository(session)
            if tool_name:
                tool_calls = await tool_repo.get_by_tool_name(conversation_id, tool_name)
            else:
                tool_calls = await tool_repo.get_by_conversation(conversation_id, limit=limit)

        logger.debug(
            "Retrieved tool calls: conversation_id=%r, tool=%r, count=%d",
            conversation_id,
            tool_name or "all",
            len(tool_calls),
        )
        return tool_calls

    async def healthcheck(self) -> bool:
        """Check if storage backend is healthy and accessible.

        Returns:
            True if backend is healthy, False otherwise.
        """
        return await self.storage.healthcheck()
