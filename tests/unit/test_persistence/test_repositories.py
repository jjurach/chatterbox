"""Tests for the repository pattern data access layer."""

import pytest
import pytest_asyncio
from uuid import uuid4

from chatterbox.persistence.backends.sqlite import SQLiteStorage
from chatterbox.persistence.repositories import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
    ToolCallRepository,
    ContextSnapshotRepository,
)


@pytest_asyncio.fixture
async def storage():
    """Create an in-memory SQLite storage with tables."""
    store = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
    await store.initialize()
    await store.create_tables()
    yield store
    await store.shutdown()


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.anyio
    async def test_create_user(self, storage):
        """Test creating a user."""
        async with storage.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(
                username="alice",
                email="alice@example.com",
                metadata={"preferred_language": "en"},
            )
            assert user.id is not None
            assert user.username == "alice"
            assert user.email == "alice@example.com"

    @pytest.mark.anyio
    async def test_get_user_by_id(self, storage):
        """Test retrieving a user by ID."""
        async with storage.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(username="bob")
            user_id = user.id

        async with storage.get_session() as session:
            repo = UserRepository(session)
            retrieved = await repo.get_by_id(user_id)
            assert retrieved is not None
            assert retrieved.username == "bob"

    @pytest.mark.anyio
    async def test_get_user_by_username(self, storage):
        """Test retrieving a user by username."""
        async with storage.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(username="charlie")

        async with storage.get_session() as session:
            repo = UserRepository(session)
            retrieved = await repo.get_by_username("charlie")
            assert retrieved is not None
            assert retrieved.id == user.id

    @pytest.mark.anyio
    async def test_update_user(self, storage):
        """Test updating a user."""
        async with storage.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(username="dave", email="old@example.com")
            user_id = user.id

        async with storage.get_session() as session:
            repo = UserRepository(session)
            updated = await repo.update(
                user_id, email="new@example.com"
            )
            assert updated is not None
            assert updated.email == "new@example.com"

    @pytest.mark.anyio
    async def test_delete_user(self, storage):
        """Test deleting a user."""
        async with storage.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(username="eve")
            user_id = user.id

        async with storage.get_session() as session:
            repo = UserRepository(session)
            deleted = await repo.delete(user_id)
            assert deleted is True

        async with storage.get_session() as session:
            repo = UserRepository(session)
            retrieved = await repo.get_by_id(user_id)
            assert retrieved is None


class TestConversationRepository:
    """Tests for ConversationRepository."""

    @pytest.mark.anyio
    async def test_create_conversation(self, storage):
        """Test creating a conversation."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create(
                language="en",
                device="living_room",
            )
            assert conv.id is not None
            assert conv.conversation_id is not None
            assert conv.language == "en"
            assert conv.device == "living_room"

    @pytest.mark.anyio
    async def test_create_conversation_with_user(self, storage):
        """Test creating a conversation for a user."""
        user_id = str(uuid4())
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create(user_id=user_id)
            assert conv.user_id == user_id

    @pytest.mark.anyio
    async def test_get_conversation_by_id(self, storage):
        """Test retrieving a conversation by UUID."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create(language="en")
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            retrieved = await repo.get_by_id(conv_id)
            assert retrieved is not None
            assert retrieved.language == "en"

    @pytest.mark.anyio
    async def test_get_conversation_by_conversation_id(self, storage):
        """Test retrieving a conversation by conversation_id."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id_str = conv.conversation_id

        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            retrieved = await repo.get_by_conversation_id(conv_id_str)
            assert retrieved is not None
            assert retrieved.id == conv.id

    @pytest.mark.anyio
    async def test_get_conversations_by_user(self, storage):
        """Test listing conversations for a user."""
        user_id = str(uuid4())
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            await repo.create(user_id=user_id)
            await repo.create(user_id=user_id)
            await repo.create(user_id=str(uuid4()))  # Different user

        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            user_convs = await repo.get_by_user_id(user_id)
            assert len(user_convs) == 2

    @pytest.mark.anyio
    async def test_update_conversation(self, storage):
        """Test updating a conversation."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create(device="old_device")
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            updated = await repo.update(conv_id, device="new_device")
            assert updated is not None
            assert updated.device == "new_device"

    @pytest.mark.anyio
    async def test_delete_conversation(self, storage):
        """Test deleting a conversation."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            deleted = await repo.delete(conv_id)
            assert deleted is True

        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            retrieved = await repo.get_by_id(conv_id)
            assert retrieved is None


class TestMessageRepository:
    """Tests for MessageRepository."""

    @pytest.mark.anyio
    async def test_add_message(self, storage):
        """Test adding a message."""
        conv_id = str(uuid4())
        async with storage.get_session() as session:
            # Create conversation first
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = MessageRepository(session)
            msg = await repo.add(
                conversation_id=conv_id,
                role="user",
                content="Hello!",
            )
            assert msg.id is not None
            assert msg.sequence == 1
            assert msg.role == "user"
            assert msg.content == "Hello!"

    @pytest.mark.anyio
    async def test_message_auto_sequence(self, storage):
        """Test that messages get auto-sequenced."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            msg1 = await msg_repo.add(
                conversation_id=conv_id,
                role="user",
                content="First",
            )
            msg2 = await msg_repo.add(
                conversation_id=conv_id,
                role="assistant",
                content="Response",
            )
            assert msg1.sequence == 1
            assert msg2.sequence == 2

    @pytest.mark.anyio
    async def test_get_messages_by_conversation(self, storage):
        """Test retrieving messages for a conversation."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            await msg_repo.add(conversation_id=conv_id, role="user", content="Hi")
            await msg_repo.add(conversation_id=conv_id, role="assistant", content="Hello")

        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            messages = await msg_repo.get_by_conversation(conv_id)
            assert len(messages) == 2
            assert messages[0].sequence == 1
            assert messages[1].sequence == 2

    @pytest.mark.anyio
    async def test_delete_old_messages(self, storage):
        """Test deleting old messages (retention policy)."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            for i in range(5):
                await msg_repo.add(
                    conversation_id=conv_id,
                    role="user",
                    content=f"Message {i}",
                )

        # Delete old messages, keeping only the 2 most recent
        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            deleted = await msg_repo.delete_old(conv_id, keep_count=2)
            assert deleted == 3

        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            messages = await msg_repo.get_by_conversation(conv_id)
            assert len(messages) == 2
            assert messages[0].content == "Message 3"
            assert messages[1].content == "Message 4"

    @pytest.mark.anyio
    async def test_delete_message(self, storage):
        """Test deleting a single message."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            msg = await msg_repo.add(
                conversation_id=conv_id,
                role="user",
                content="Test",
            )
            msg_id = msg.id

        async with storage.get_session() as session:
            msg_repo = MessageRepository(session)
            deleted = await msg_repo.delete(msg_id)
            assert deleted is True


class TestToolCallRepository:
    """Tests for ToolCallRepository."""

    @pytest.mark.anyio
    async def test_add_tool_call(self, storage):
        """Test logging a tool call."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ToolCallRepository(session)
            call = await repo.add(
                conversation_id=conv_id,
                call_id="call_123",
                tool_name="get_weather",
                arguments={"location": "NYC"},
                result="Sunny",
                duration_ms=100,
            )
            assert call.id is not None
            assert call.tool_name == "get_weather"
            assert call.result == "Sunny"

    @pytest.mark.anyio
    async def test_add_tool_call_with_error(self, storage):
        """Test logging a failed tool call."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ToolCallRepository(session)
            call = await repo.add(
                conversation_id=conv_id,
                call_id="call_456",
                tool_name="get_news",
                arguments={},
                error="API timeout",
            )
            assert call.error == "API timeout"
            assert call.result is None

    @pytest.mark.anyio
    async def test_get_tool_calls_by_conversation(self, storage):
        """Test retrieving tool calls for a conversation."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ToolCallRepository(session)
            await repo.add(
                conversation_id=conv_id,
                call_id="c1",
                tool_name="weather",
                arguments={},
            )
            await repo.add(
                conversation_id=conv_id,
                call_id="c2",
                tool_name="news",
                arguments={},
            )

        async with storage.get_session() as session:
            repo = ToolCallRepository(session)
            calls = await repo.get_by_conversation(conv_id)
            assert len(calls) == 2

    @pytest.mark.anyio
    async def test_get_tool_calls_by_tool_name(self, storage):
        """Test retrieving calls to a specific tool."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ToolCallRepository(session)
            await repo.add(
                conversation_id=conv_id,
                call_id="c1",
                tool_name="weather",
                arguments={},
            )
            await repo.add(
                conversation_id=conv_id,
                call_id="c2",
                tool_name="weather",
                arguments={},
            )
            await repo.add(
                conversation_id=conv_id,
                call_id="c3",
                tool_name="news",
                arguments={},
            )

        async with storage.get_session() as session:
            repo = ToolCallRepository(session)
            weather_calls = await repo.get_by_tool_name(conv_id, "weather")
            assert len(weather_calls) == 2


class TestContextSnapshotRepository:
    """Tests for ContextSnapshotRepository."""

    @pytest.mark.anyio
    async def test_create_snapshot(self, storage):
        """Test creating a context snapshot."""
        context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ContextSnapshotRepository(session)
            snapshot = await repo.create(
                conversation_id=conv_id,
                context_window=context,
                message_sequence=2,
                metadata={"reason": "truncation"},
            )
            assert snapshot.id is not None
            assert len(snapshot.context_window) == 2
            assert snapshot.metadata["reason"] == "truncation"

    @pytest.mark.anyio
    async def test_get_snapshots_by_conversation(self, storage):
        """Test retrieving snapshots for a conversation."""
        async with storage.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create()
            conv_id = conv.id

        async with storage.get_session() as session:
            repo = ContextSnapshotRepository(session)
            await repo.create(
                conversation_id=conv_id,
                context_window=[],
                message_sequence=1,
            )
            await repo.create(
                conversation_id=conv_id,
                context_window=[],
                message_sequence=2,
            )

        async with storage.get_session() as session:
            repo = ContextSnapshotRepository(session)
            snapshots = await repo.get_by_conversation(conv_id)
            assert len(snapshots) == 2
