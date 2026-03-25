"""
SQLAlchemy ORM models for Chatterbox persistence.

Defines the database schema for storing conversations, messages, tool calls,
and context snapshots. Uses SQLAlchemy 2.0+ declarative syntax with async support.

Key design decisions:
- UUID primary keys for all tables (distributed-friendly)
- JSON columns for flexible metadata (model params, tool results, etc.)
- Foreign keys with CASCADE delete for referential integrity
- Indexed frequently-queried columns (conversation_id, created_at, user_id)
- Nullable timestamps allow for context snapshots without explicit timing
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    UUID,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


class User(Base):
    """User account in the system.

    Represents a user interacting with the Chatterbox assistant. This allows
    multi-user scenarios where different users have separate conversation histories.

    Attributes:
        id: UUID primary key.
        username: Unique username for login/identification.
        email: Optional email address.
        created_at: Timestamp when the user was created.
        user_metadata: JSON field for custom user attributes (preferences, settings, etc.).
    """

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_username", "username", unique=True),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    user_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id!r}, username={self.username!r})>"


class Conversation(Base):
    """A conversation session with the assistant.

    Each conversation represents a multi-turn interaction with the LLM.
    Conversations can be tied to a specific user and include metadata about
    the session (language, device, etc.).

    Attributes:
        id: UUID primary key.
        user_id: FK to User.id (nullable for anonymous conversations).
        conversation_id: String identifier returned to clients (may differ from UUID id).
        language: BCP-47 language tag (e.g., "en", "es-ES").
        device: Device identifier (e.g., "living_room_box", "kitchen_speaker").
        created_at: Timestamp when conversation started.
        updated_at: Timestamp of last message in conversation.
        conversation_metadata: JSON field (model variant, system prompt hash, etc.).
    """

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_conversation_id", "conversation_id", unique=True),
        Index("ix_conversations_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    conversation_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user: Mapped[User | None] = relationship("User", back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    tool_calls: Mapped[list[ToolCall]] = relationship(
        "ToolCall", back_populates="conversation", cascade="all, delete-orphan"
    )
    context_snapshots: Mapped[list[ContextSnapshot]] = relationship(
        "ContextSnapshot", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id!r}, conversation_id={self.conversation_id!r})>"


class Message(Base):
    """A single message in a conversation turn.

    Messages are ordered by sequence number within each conversation. Each message
    has a role (user, assistant, or system) and content. Messages are preserved
    as part of the conversation history for context management and replay.

    Attributes:
        id: UUID primary key.
        conversation_id: FK to Conversation.id.
        sequence: Order of message within conversation (1-indexed).
        role: "user", "assistant", or "system".
        content: The message text.
        created_at: Timestamp when message was created.
        message_metadata: JSON field (token count, latency, model variant, etc.).
    """

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_conversation_sequence", "conversation_id", "sequence"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    message_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id!r}, role={self.role!r}, seq={self.sequence})>"


class ToolCall(Base):
    """A tool invocation by the LLM or result from a tool.

    Captures both the LLM's request to invoke a tool and the result returned
    by the tool dispatcher. Used for auditing, debugging, and analytics.

    Attributes:
        id: UUID primary key.
        conversation_id: FK to Conversation.id.
        message_id: FK to Message.id (message containing tool_calls).
        call_id: Tool call ID from OpenAI (for correlation).
        tool_name: Name of the tool invoked.
        arguments: JSON dict of input arguments.
        result: Text result returned by the tool.
        error: Error message if tool execution failed.
        duration_ms: Time taken to execute tool (milliseconds).
        created_at: Timestamp when tool call was made.
        call_metadata: JSON field for additional call metadata.
    """

    __tablename__ = "tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_conversation_id", "conversation_id"),
        Index("ix_tool_calls_message_id", "message_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False
    )
    message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("messages.id"), nullable=True
    )
    call_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    call_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="tool_calls"
    )
    message: Mapped[Message | None] = relationship("Message")

    def __repr__(self) -> str:
        return f"<ToolCall(id={self.id!r}, tool_name={self.tool_name!r})>"


class ContextSnapshot(Base):
    """A snapshot of conversation context at a point in time.

    Captures the state of context for analytics, debugging, or context
    persistence. Snapshots are created at significant points (e.g., before
    context truncation, after a turn completes, etc.).

    Attributes:
        id: UUID primary key.
        conversation_id: FK to Conversation.id.
        message_sequence: Message sequence number when snapshot was taken.
        context_window: JSON array of messages in the context window.
        snapshot_metadata: JSON dict (reason for snapshot, truncation count, etc.).
        created_at: Timestamp when snapshot was taken.
    """

    __tablename__ = "context_snapshots"
    __table_args__ = (Index("ix_context_snapshots_conversation_id", "conversation_id"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False
    )
    message_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_window: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    snapshot_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="context_snapshots"
    )

    def __repr__(self) -> str:
        return f"<ContextSnapshot(id={self.id!r}, message_seq={self.message_sequence})>"
