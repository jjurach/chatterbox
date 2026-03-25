"""
Repository pattern for data access in Chatterbox persistence.

Implements the Repository pattern to provide a clean abstraction over
ORM operations. Repositories handle:
- CRUD operations (Create, Read, Update, Delete)
- Query building and filtering
- Data transformation between ORM models and domain objects
- Pagination and sorting

Benefits:
1. Decouples application logic from SQLAlchemy specifics
2. Makes testing easier (can mock repositories)
3. Provides a single point to optimize queries
4. Enables batch operations and transactions

All repository methods are async to match Epic 4's async/await pattern.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.schema import (
    Conversation,
    ContextSnapshot,
    Message,
    ToolCall,
    User,
)

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User operations.

    Methods for creating, retrieving, and updating user accounts.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a session.

        Args:
            session: AsyncSession bound to a database connection.
        """
        self.session = session

    async def create(
        self,
        username: str,
        email: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        """Create a new user.

        Args:
            username: Unique username.
            email: Optional email address.
            metadata: Optional JSON metadata dict.

        Returns:
            The created User object.

        Raises:
            Exception: If username already exists (unique constraint violation).
        """
        user = User(
            id=str(uuid4()),
            username=username,
            email=email,
            metadata=metadata or {},
        )
        self.session.add(user)
        await self.session.flush()
        logger.info("Created user: id=%s, username=%s", user.id, username)
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by ID.

        Args:
            user_id: The user's UUID.

        Returns:
            The User object, or None if not found.
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by username.

        Args:
            username: The username to look up.

        Returns:
            The User object, or None if not found.
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    async def update(self, user_id: str, **kwargs) -> User | None:
        """Update a user.

        Args:
            user_id: The user's UUID.
            **kwargs: Fields to update (email, metadata, etc.).

        Returns:
            The updated User object, or None if not found.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self.session.flush()
        logger.info("Updated user: id=%s", user_id)
        return user

    async def delete(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: The user's UUID.

        Returns:
            True if the user was deleted, False if not found.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False

        await self.session.delete(user)
        await self.session.flush()
        logger.info("Deleted user: id=%s", user_id)
        return True


class ConversationRepository:
    """Repository for Conversation operations.

    Methods for creating, retrieving, updating, and listing conversations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a session.

        Args:
            session: AsyncSession bound to a database connection.
        """
        self.session = session

    async def create(
        self,
        user_id: str | None = None,
        conversation_id: str | None = None,
        language: str = "en",
        device: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            user_id: Optional FK to User.id.
            conversation_id: Optional UUID string (usually auto-generated).
                If not provided, one is generated.
            language: BCP-47 language tag (default: "en").
            device: Optional device identifier.
            metadata: Optional JSON metadata.

        Returns:
            The created Conversation object.
        """
        conv_id = conversation_id or str(uuid4())
        conversation = Conversation(
            id=str(uuid4()),
            user_id=user_id,
            conversation_id=conv_id,
            language=language,
            device=device,
            metadata=metadata or {},
        )
        self.session.add(conversation)
        await self.session.flush()
        logger.info(
            "Created conversation: id=%s, conversation_id=%s",
            conversation.id,
            conv_id,
        )
        return conversation

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        """Retrieve a conversation by UUID id.

        Args:
            conversation_id: The conversation's UUID.

        Returns:
            The Conversation object, or None if not found.
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalars().first()

    async def get_by_conversation_id(
        self, conversation_id: str
    ) -> Conversation | None:
        """Retrieve a conversation by conversation_id (client-facing string).

        Args:
            conversation_id: The client-facing conversation ID.

        Returns:
            The Conversation object, or None if not found.
        """
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.conversation_id == conversation_id
            )
        )
        return result.scalars().first()

    async def get_by_user_id(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> list[Conversation]:
        """List conversations for a user.

        Args:
            user_id: The user's UUID.
            limit: Maximum number of results (default: 100).
            offset: Number of results to skip (default: 0).

        Returns:
            List of Conversation objects, ordered by most recent first.
        """
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update(
        self, conversation_id: str, **kwargs
    ) -> Conversation | None:
        """Update a conversation.

        Args:
            conversation_id: The conversation's UUID.
            **kwargs: Fields to update (language, device, metadata, etc.).

        Returns:
            The updated Conversation object, or None if not found.
        """
        conv = await self.get_by_id(conversation_id)
        if conv is None:
            return None

        for key, value in kwargs.items():
            if hasattr(conv, key):
                setattr(conv, key, value)

        # Update the updated_at timestamp
        conv.updated_at = datetime.utcnow()
        await self.session.flush()
        logger.info("Updated conversation: id=%s", conversation_id)
        return conv

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation (and all related messages/tool_calls).

        Args:
            conversation_id: The conversation's UUID.

        Returns:
            True if the conversation was deleted, False if not found.
        """
        conv = await self.get_by_id(conversation_id)
        if conv is None:
            return False

        await self.session.delete(conv)
        await self.session.flush()
        logger.info("Deleted conversation: id=%s", conversation_id)
        return True


class MessageRepository:
    """Repository for Message operations.

    Methods for adding, retrieving, and deleting messages in conversations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a session.

        Args:
            session: AsyncSession bound to a database connection.
        """
        self.session = session

    async def add(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Add a message to a conversation.

        Automatically assigns the next sequence number.

        Args:
            conversation_id: FK to Conversation.id.
            role: "user", "assistant", or "system".
            content: The message text.
            metadata: Optional JSON metadata (token count, latency, etc.).

        Returns:
            The created Message object.

        Raises:
            ValueError: If the role is invalid.
        """
        if role not in ("user", "assistant", "system"):
            raise ValueError(f"Invalid role: {role}")

        # Get the next sequence number
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.sequence))
            .limit(1)
        )
        last_message = result.scalars().first()
        next_sequence = (last_message.sequence if last_message else 0) + 1

        message = Message(
            id=str(uuid4()),
            conversation_id=conversation_id,
            sequence=next_sequence,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.session.add(message)
        await self.session.flush()
        logger.debug(
            "Added message: conversation_id=%s, sequence=%d, role=%s",
            conversation_id,
            next_sequence,
            role,
        )
        return message

    async def get_by_id(self, message_id: str) -> Message | None:
        """Retrieve a message by ID.

        Args:
            message_id: The message's UUID.

        Returns:
            The Message object, or None if not found.
        """
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalars().first()

    async def get_by_conversation(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> list[Message]:
        """Retrieve all messages in a conversation.

        Args:
            conversation_id: FK to Conversation.id.
            limit: Optional maximum number of recent messages to return.

        Returns:
            List of Message objects, ordered by sequence number.
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence)
        )
        if limit is not None:
            query = (
                query.order_by(desc(Message.sequence))
                .limit(limit)
                .order_by(Message.sequence)
            )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_old(
        self, conversation_id: str, keep_count: int = 0
    ) -> int:
        """Delete old messages, keeping only the most recent ones.

        Useful for implementing retention policies.

        Args:
            conversation_id: FK to Conversation.id.
            keep_count: Number of most recent messages to keep.

        Returns:
            Number of messages deleted.
        """
        # Get all messages, ordered by sequence
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.sequence))
        )
        all_messages = result.scalars().all()

        if len(all_messages) <= keep_count:
            return 0

        # Delete the oldest messages
        to_delete = all_messages[keep_count:]
        for msg in to_delete:
            await self.session.delete(msg)

        await self.session.flush()
        deleted_count = len(to_delete)
        logger.info(
            "Deleted %d old messages from conversation %s",
            deleted_count,
            conversation_id,
        )
        return deleted_count

    async def delete(self, message_id: str) -> bool:
        """Delete a message.

        Args:
            message_id: The message's UUID.

        Returns:
            True if the message was deleted, False if not found.
        """
        message = await self.get_by_id(message_id)
        if message is None:
            return False

        await self.session.delete(message)
        await self.session.flush()
        logger.info("Deleted message: id=%s", message_id)
        return True


class ToolCallRepository:
    """Repository for ToolCall operations.

    Methods for logging and retrieving tool invocations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a session.

        Args:
            session: AsyncSession bound to a database connection.
        """
        self.session = session

    async def add(
        self,
        conversation_id: str,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        message_id: str | None = None,
        result: str | None = None,
        error: str | None = None,
        duration_ms: int | None = None,
    ) -> ToolCall:
        """Log a tool call.

        Args:
            conversation_id: FK to Conversation.id.
            call_id: Tool call ID from the LLM.
            tool_name: Name of the tool.
            arguments: JSON dict of input arguments.
            message_id: Optional FK to the Message containing tool_calls.
            result: Optional result from the tool.
            error: Optional error message if tool failed.
            duration_ms: Optional execution time in milliseconds.

        Returns:
            The created ToolCall object.
        """
        tool_call = ToolCall(
            id=str(uuid4()),
            conversation_id=conversation_id,
            message_id=message_id,
            call_id=call_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )
        self.session.add(tool_call)
        await self.session.flush()
        logger.debug(
            "Logged tool call: conversation_id=%s, tool_name=%s, call_id=%s",
            conversation_id,
            tool_name,
            call_id,
        )
        return tool_call

    async def get_by_id(self, tool_call_id: str) -> ToolCall | None:
        """Retrieve a tool call by ID.

        Args:
            tool_call_id: The tool call's UUID.

        Returns:
            The ToolCall object, or None if not found.
        """
        result = await self.session.execute(
            select(ToolCall).where(ToolCall.id == tool_call_id)
        )
        return result.scalars().first()

    async def get_by_conversation(
        self, conversation_id: str, limit: int = 100
    ) -> list[ToolCall]:
        """Retrieve tool calls for a conversation.

        Args:
            conversation_id: FK to Conversation.id.
            limit: Maximum number of results.

        Returns:
            List of ToolCall objects, ordered by most recent first.
        """
        result = await self.session.execute(
            select(ToolCall)
            .where(ToolCall.conversation_id == conversation_id)
            .order_by(desc(ToolCall.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_tool_name(
        self, conversation_id: str, tool_name: str
    ) -> list[ToolCall]:
        """Retrieve all calls to a specific tool in a conversation.

        Args:
            conversation_id: FK to Conversation.id.
            tool_name: Name of the tool.

        Returns:
            List of ToolCall objects.
        """
        result = await self.session.execute(
            select(ToolCall).where(
                (ToolCall.conversation_id == conversation_id)
                & (ToolCall.tool_name == tool_name)
            )
        )
        return result.scalars().all()


class ContextSnapshotRepository:
    """Repository for ContextSnapshot operations.

    Methods for creating and retrieving context snapshots.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a session.

        Args:
            session: AsyncSession bound to a database connection.
        """
        self.session = session

    async def create(
        self,
        conversation_id: str,
        context_window: list[dict[str, Any]],
        message_sequence: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContextSnapshot:
        """Create a context snapshot.

        Args:
            conversation_id: FK to Conversation.id.
            context_window: The context messages at the time of snapshot.
            message_sequence: Optional message sequence number.
            metadata: Optional JSON metadata (reason, truncation_count, etc.).

        Returns:
            The created ContextSnapshot object.
        """
        snapshot = ContextSnapshot(
            id=str(uuid4()),
            conversation_id=conversation_id,
            message_sequence=message_sequence,
            context_window=context_window,
            metadata=metadata or {},
        )
        self.session.add(snapshot)
        await self.session.flush()
        logger.debug(
            "Created context snapshot: conversation_id=%s, sequence=%s",
            conversation_id,
            message_sequence,
        )
        return snapshot

    async def get_by_id(self, snapshot_id: str) -> ContextSnapshot | None:
        """Retrieve a snapshot by ID.

        Args:
            snapshot_id: The snapshot's UUID.

        Returns:
            The ContextSnapshot object, or None if not found.
        """
        result = await self.session.execute(
            select(ContextSnapshot).where(ContextSnapshot.id == snapshot_id)
        )
        return result.scalars().first()

    async def get_by_conversation(
        self, conversation_id: str, limit: int = 100
    ) -> list[ContextSnapshot]:
        """Retrieve snapshots for a conversation.

        Args:
            conversation_id: FK to Conversation.id.
            limit: Maximum number of results.

        Returns:
            List of ContextSnapshot objects, ordered by most recent first.
        """
        result = await self.session.execute(
            select(ContextSnapshot)
            .where(ContextSnapshot.conversation_id == conversation_id)
            .order_by(desc(ContextSnapshot.created_at))
            .limit(limit)
        )
        return result.scalars().all()
