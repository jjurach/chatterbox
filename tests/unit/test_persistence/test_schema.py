"""Tests for SQLAlchemy ORM models and schema validation."""

import pytest
from datetime import datetime
from uuid import uuid4

from chatterbox.persistence.schema import (
    User,
    Conversation,
    Message,
    ToolCall,
    ContextSnapshot,
    Base,
)


class TestUserModel:
    """Tests for the User ORM model."""

    def test_user_creation(self):
        """Test creating a User instance."""
        user_id = str(uuid4())
        user = User(
            id=user_id,
            username="testuser",
            email="test@example.com",
            user_metadata={"preferred_language": "en"},
        )
        assert user.id == user_id
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.user_metadata["preferred_language"] == "en"

    def test_user_minimal(self):
        """Test User model with minimal fields."""
        user = User(id=str(uuid4()), username="alice")
        assert user.email is None
        assert user.username == "alice"

    def test_user_repr(self):
        """Test User string representation."""
        user = User(id="123", username="bob")
        assert "User" in repr(user)
        assert "bob" in repr(user)


class TestConversationModel:
    """Tests for the Conversation ORM model."""

    def test_conversation_creation(self):
        """Test creating a Conversation instance."""
        conv = Conversation(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            language="en",
            device="living_room",
            conversation_metadata={"system_prompt_hash": "abc123"},
        )
        assert conv.language == "en"
        assert conv.device == "living_room"
        assert conv.conversation_metadata["system_prompt_hash"] == "abc123"

    def test_conversation_minimal(self):
        """Test Conversation model with minimal fields."""
        conv_id = str(uuid4())
        conv = Conversation(
            id=str(uuid4()), conversation_id=conv_id, language="en"
        )
        assert conv.user_id is None
        assert conv.language == "en"
        assert conv.device is None
        assert conv.conversation_id == conv_id

    def test_conversation_repr(self):
        """Test Conversation string representation."""
        conv_id = str(uuid4())
        conv = Conversation(id=str(uuid4()), conversation_id=conv_id)
        assert "Conversation" in repr(conv)
        assert conv_id[:8] in repr(conv)


class TestMessageModel:
    """Tests for the Message ORM model."""

    def test_message_creation(self):
        """Test creating a Message instance."""
        msg = Message(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sequence=1,
            role="user",
            content="Hello, assistant!",
            message_metadata={"token_count": 5},
        )
        assert msg.sequence == 1
        assert msg.role == "user"
        assert msg.content == "Hello, assistant!"
        assert msg.message_metadata["token_count"] == 5

    def test_message_roles(self):
        """Test message with different roles."""
        conv_id = str(uuid4())
        for role in ("user", "assistant", "system"):
            msg = Message(
                id=str(uuid4()),
                conversation_id=conv_id,
                sequence=1,
                role=role,
                content=f"This is a {role} message",
            )
            assert msg.role == role

    def test_message_repr(self):
        """Test Message string representation."""
        msg = Message(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sequence=1,
            role="assistant",
            content="Hello!",
        )
        assert "Message" in repr(msg)
        assert "assistant" in repr(msg)


class TestToolCallModel:
    """Tests for the ToolCall ORM model."""

    def test_tool_call_creation(self):
        """Test creating a ToolCall instance."""
        call = ToolCall(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            call_id="call_123",
            tool_name="get_weather",
            arguments={"location": "New York"},
            result="Sunny, 72F",
            duration_ms=150,
        )
        assert call.call_id == "call_123"
        assert call.tool_name == "get_weather"
        assert call.arguments["location"] == "New York"
        assert call.result == "Sunny, 72F"
        assert call.duration_ms == 150
        assert call.error is None

    def test_tool_call_with_error(self):
        """Test tool call that failed."""
        call = ToolCall(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            call_id="call_456",
            tool_name="get_news",
            arguments={"topic": "tech"},
            error="API rate limit exceeded",
        )
        assert call.error is not None
        assert call.result is None

    def test_tool_call_repr(self):
        """Test ToolCall string representation."""
        call = ToolCall(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            call_id="call_789",
            tool_name="get_weather",
            arguments={},
        )
        assert "ToolCall" in repr(call)
        assert "get_weather" in repr(call)


class TestContextSnapshotModel:
    """Tests for the ContextSnapshot ORM model."""

    def test_context_snapshot_creation(self):
        """Test creating a ContextSnapshot instance."""
        context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        snapshot = ContextSnapshot(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            message_sequence=2,
            context_window=context,
            snapshot_metadata={"truncation_count": 0, "reason": "manual"},
        )
        assert len(snapshot.context_window) == 2
        assert snapshot.message_sequence == 2
        assert snapshot.snapshot_metadata["reason"] == "manual"

    def test_context_snapshot_minimal(self):
        """Test ContextSnapshot model with minimal fields."""
        snapshot = ContextSnapshot(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            context_window=[],
        )
        assert snapshot.message_sequence is None
        assert snapshot.context_window == []

    def test_context_snapshot_repr(self):
        """Test ContextSnapshot string representation."""
        snapshot = ContextSnapshot(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            message_sequence=5,
            context_window=[],
        )
        assert "ContextSnapshot" in repr(snapshot)
        assert "5" in repr(snapshot)


class TestSchemaMetadata:
    """Tests for schema metadata (tables, columns, indexes)."""

    def test_all_models_in_registry(self):
        """Test that all models are registered in Base.metadata."""
        model_names = {table.name for table in Base.metadata.tables.values()}
        expected_names = {"users", "conversations", "messages", "tool_calls", "context_snapshots"}
        assert expected_names == model_names

    def test_user_table_columns(self):
        """Test User table has expected columns."""
        user_table = Base.metadata.tables["users"]
        column_names = {col.name for col in user_table.columns}
        expected = {"id", "username", "email", "created_at", "user_metadata"}
        assert expected == column_names

    def test_conversation_table_columns(self):
        """Test Conversation table has expected columns."""
        conv_table = Base.metadata.tables["conversations"]
        column_names = {col.name for col in conv_table.columns}
        expected = {
            "id",
            "user_id",
            "conversation_id",
            "language",
            "device",
            "created_at",
            "updated_at",
            "conversation_metadata",
        }
        assert expected == column_names

    def test_message_table_columns(self):
        """Test Message table has expected columns."""
        msg_table = Base.metadata.tables["messages"]
        column_names = {col.name for col in msg_table.columns}
        expected = {
            "id",
            "conversation_id",
            "sequence",
            "role",
            "content",
            "created_at",
            "message_metadata",
        }
        assert expected == column_names

    def test_tool_call_table_columns(self):
        """Test ToolCall table has expected columns."""
        call_table = Base.metadata.tables["tool_calls"]
        column_names = {col.name for col in call_table.columns}
        expected = {
            "id",
            "conversation_id",
            "message_id",
            "call_id",
            "tool_name",
            "arguments",
            "result",
            "error",
            "duration_ms",
            "created_at",
            "call_metadata",
        }
        assert expected == column_names

    def test_context_snapshot_table_columns(self):
        """Test ContextSnapshot table has expected columns."""
        snap_table = Base.metadata.tables["context_snapshots"]
        column_names = {col.name for col in snap_table.columns}
        expected = {
            "id",
            "conversation_id",
            "message_sequence",
            "context_window",
            "snapshot_metadata",
            "created_at",
        }
        assert expected == column_names

    def test_primary_keys(self):
        """Test all tables have UUID primary keys."""
        for table_name, table in Base.metadata.tables.items():
            pk_cols = [col for col in table.columns if col.primary_key]
            assert len(pk_cols) == 1, f"{table_name} should have exactly one PK"
            assert "id" in [col.name for col in pk_cols]

    def test_json_columns(self):
        """Test JSON columns are properly defined."""
        # Conversation metadata
        conv_table = Base.metadata.tables["conversations"]
        metadata_col = conv_table.c.conversation_metadata
        assert "JSON" in str(metadata_col.type)

        # Message metadata
        msg_table = Base.metadata.tables["messages"]
        metadata_col = msg_table.c.message_metadata
        assert "JSON" in str(metadata_col.type)

        # ToolCall arguments and call_metadata
        call_table = Base.metadata.tables["tool_calls"]
        assert "JSON" in str(call_table.c.arguments.type)
        assert "JSON" in str(call_table.c.call_metadata.type)

        # ContextSnapshot context_window
        snap_table = Base.metadata.tables["context_snapshots"]
        assert "JSON" in str(snap_table.c.context_window.type)
        assert "JSON" in str(snap_table.c.snapshot_metadata.type)

    def test_foreign_key_constraints(self):
        """Test foreign key relationships."""
        # Conversations.user_id -> Users.id
        conv_table = Base.metadata.tables["conversations"]
        fks = list(conv_table.foreign_keys)
        fk_names = {fk.column.name for fk in fks}
        assert "id" in fk_names  # FK to users.id

        # Messages.conversation_id -> Conversations.id
        msg_table = Base.metadata.tables["messages"]
        fks = list(msg_table.foreign_keys)
        fk_names = {fk.column.name for fk in fks}
        assert "id" in fk_names  # FK to conversations.id

        # ToolCalls.conversation_id and message_id
        call_table = Base.metadata.tables["tool_calls"]
        fks = list(call_table.foreign_keys)
        fk_cols = {fk.parent.name for fk in fks}
        assert "conversation_id" in fk_cols
        assert "message_id" in fk_cols

    def test_unique_constraints(self):
        """Test unique constraints."""
        user_table = Base.metadata.tables["users"]
        # Username should be unique
        username_col = user_table.c.username
        assert username_col.unique

        # Conversation ID should be unique
        conv_table = Base.metadata.tables["conversations"]
        conv_id_col = conv_table.c.conversation_id
        assert conv_id_col.unique
