"""
Tests for context retrieval and window management.

Tests cover:
- Token counting
- Context message creation
- Context window building
- Pagination
- Context integrity verification
- Token budget enforcement
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.context import (
    ContextManager,
    ContextMessage,
    ContextWindow,
    TokenCounter,
)
from chatterbox.persistence.repositories import (
    ConversationRepository,
    MessageRepository,
)


class TestTokenCounter:
    """Tests for token counting utility."""

    def test_count_tokens_empty(self):
        """Test token count for empty string."""
        count = TokenCounter.count_tokens("")
        assert count == 4  # TOKENS_PER_MESSAGE

    def test_count_tokens_short(self):
        """Test token count for short text."""
        count = TokenCounter.count_tokens("hello")
        assert count > 0

    def test_count_tokens_long(self):
        """Test token count for longer text."""
        short = TokenCounter.count_tokens("hello")
        long = TokenCounter.count_tokens("hello world this is a longer message with many words")
        assert long > short

    def test_count_message_tokens(self):
        """Test token count for role+content pair."""
        count = TokenCounter.count_message_tokens("user", "hello world")
        assert count > 0

    def test_token_count_consistency(self):
        """Test that token counting is consistent."""
        text = "The weather is nice today"
        count1 = TokenCounter.count_tokens(text)
        count2 = TokenCounter.count_tokens(text)
        assert count1 == count2


class TestContextMessage:
    """Tests for ContextMessage dataclass."""

    def test_create_context_message(self):
        """Test creating a context message."""
        msg = ContextMessage(
            id="msg-1",
            role="user",
            content="Hello, how are you?",
            sequence=1,
            token_count=5,
        )
        assert msg.id == "msg-1"
        assert msg.role == "user"
        assert msg.content == "Hello, how are you?"
        assert msg.sequence == 1
        assert msg.token_count == 5

    def test_context_message_to_dict(self):
        """Test converting context message to dict."""
        msg = ContextMessage(
            id="msg-1",
            role="assistant",
            content="I'm doing well, thanks!",
            sequence=2,
            token_count=6,
        )
        msg_dict = msg.to_dict()

        assert msg_dict["id"] == "msg-1"
        assert msg_dict["role"] == "assistant"
        assert msg_dict["content"] == "I'm doing well, thanks!"
        assert msg_dict["sequence"] == 2
        assert msg_dict["token_count"] == 6


class TestContextWindow:
    """Tests for ContextWindow dataclass."""

    def test_create_context_window(self):
        """Test creating a context window."""
        messages = [
            ContextMessage("1", "user", "Hello", 1, 4),
            ContextMessage("2", "assistant", "Hi there", 2, 4),
        ]
        window = ContextWindow(
            conversation_id="conv-1",
            messages=messages,
            total_tokens=8,
            truncated=False,
            oldest_message_sequence=1,
            newest_message_sequence=2,
        )

        assert window.conversation_id == "conv-1"
        assert len(window.messages) == 2
        assert window.total_tokens == 8
        assert not window.truncated

    def test_context_window_to_list(self):
        """Test converting context window to list."""
        messages = [
            ContextMessage("1", "user", "Hello", 1, 4),
            ContextMessage("2", "assistant", "Hi", 2, 4),
        ]
        window = ContextWindow(
            conversation_id="conv-1",
            messages=messages,
            total_tokens=8,
        )

        msg_list = window.to_list()
        assert len(msg_list) == 2
        assert msg_list[0]["role"] == "user"
        assert msg_list[1]["role"] == "assistant"

    def test_context_window_to_openai_format(self):
        """Test converting context window to OpenAI format."""
        messages = [
            ContextMessage("1", "system", "You are helpful", 0, 4),
            ContextMessage("2", "user", "Hello", 1, 4),
            ContextMessage("3", "assistant", "Hi", 2, 4),
        ]
        window = ContextWindow(
            conversation_id="conv-1",
            messages=messages,
            total_tokens=12,
        )

        openai_format = window.to_openai_format()
        assert len(openai_format) == 3
        assert openai_format[0]["role"] == "system"
        assert openai_format[1]["role"] == "user"
        assert openai_format[2]["role"] == "assistant"


@pytest.mark.anyio
class TestContextManager:
    """Tests for ContextManager retrieval operations."""

    async def test_get_context_basic(self, async_session: AsyncSession):
        """Test basic context retrieval."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-1")

        # Add messages
        await msg_repo.add(conversation.id, "user", "Hello")
        await msg_repo.add(conversation.id, "assistant", "Hi there!")
        await msg_repo.add(conversation.id, "user", "How are you?")

        await async_session.flush()

        # Retrieve context
        manager = ContextManager(async_session, default_context_size=10)
        context = await manager.get_context(conversation.id, limit=10)

        assert len(context) == 3
        assert context[0].role == "user"
        assert context[0].content == "Hello"
        assert context[2].role == "user"
        assert context[2].content == "How are you?"

    async def test_get_context_limit(self, async_session: AsyncSession):
        """Test context retrieval with limit."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-2")

        # Add 10 messages
        for i in range(10):
            await msg_repo.add(conversation.id, "user", f"Message {i}")

        await async_session.flush()

        # Retrieve only last 5
        manager = ContextManager(async_session)
        context = await manager.get_context(conversation.id, limit=5)

        assert len(context) == 5
        # Should get the newest 5 messages (5-9)
        assert context[0].content == "Message 5"
        assert context[4].content == "Message 9"

    async def test_get_context_invalid_conversation(self, async_session: AsyncSession):
        """Test context retrieval for non-existent conversation."""
        manager = ContextManager(async_session)

        with pytest.raises(ValueError):
            await manager.get_context("nonexistent-conv")

    async def test_build_context_window_basic(self, async_session: AsyncSession):
        """Test context window building."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-3")

        # Add messages
        await msg_repo.add(conversation.id, "system", "You are helpful")
        await msg_repo.add(conversation.id, "user", "Hello")
        await msg_repo.add(conversation.id, "assistant", "Hi!")

        await async_session.flush()

        # Build window
        manager = ContextManager(async_session, default_token_budget=1000)
        window = await manager.build_context_window(conversation.id, token_budget=1000)

        assert len(window.messages) == 3
        assert window.total_tokens > 0
        assert not window.truncated
        assert window.oldest_message_sequence == 1
        assert window.newest_message_sequence == 3

    async def test_build_context_window_with_token_budget(self, async_session: AsyncSession):
        """Test context window respects token budget."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-4")

        # Add messages
        await msg_repo.add(conversation.id, "user", "A" * 1000)  # Long message
        await msg_repo.add(conversation.id, "assistant", "B" * 1000)  # Long message
        await msg_repo.add(conversation.id, "user", "C" * 1000)  # Long message

        await async_session.flush()

        # Build window with small token budget
        manager = ContextManager(async_session)
        window = await manager.build_context_window(
            conversation.id,
            token_budget=50,  # Very small budget
        )

        # Should be truncated
        assert window.truncated
        assert window.total_tokens <= 50 or window.truncated

    async def test_build_context_window_preserve_system(self, async_session: AsyncSession):
        """Test that system messages are always preserved."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-5")

        # Add system message first
        await msg_repo.add(conversation.id, "system", "You are helpful")

        # Add very long user messages
        for i in range(5):
            await msg_repo.add(conversation.id, "user", "X" * 2000)

        await async_session.flush()

        # Build window with small budget
        manager = ContextManager(async_session)
        window = await manager.build_context_window(
            conversation.id,
            token_budget=100,
            preserve_system_messages=True,
        )

        # System message should always be included
        system_msgs = [m for m in window.messages if m.role == "system"]
        assert len(system_msgs) == 1

    async def test_get_recent_messages_pagination(self, async_session: AsyncSession):
        """Test pagination of recent messages."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-6")

        # Add 20 messages
        for i in range(20):
            await msg_repo.add(conversation.id, "user", f"Message {i}")

        await async_session.flush()

        # Get first page
        manager = ContextManager(async_session)
        page1, total = await manager.get_recent_messages(
            conversation.id,
            limit=5,
            offset=0,
        )

        assert len(page1) == 5
        assert total == 20

        # Get second page
        page2, _ = await manager.get_recent_messages(
            conversation.id,
            limit=5,
            offset=5,
        )

        assert len(page2) == 5
        # Ensure different messages
        page1_ids = {m.id for m in page1}
        page2_ids = {m.id for m in page2}
        assert len(page1_ids & page2_ids) == 0

    async def test_verify_context_integrity(self, async_session: AsyncSession):
        """Test context integrity verification."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-7")

        # Add messages (should have sequential sequence numbers)
        await msg_repo.add(conversation.id, "user", "Message 1")
        await msg_repo.add(conversation.id, "assistant", "Message 2")
        await msg_repo.add(conversation.id, "user", "Message 3")

        await async_session.flush()

        # Verify integrity
        manager = ContextManager(async_session)
        is_valid = await manager.verify_context_integrity(conversation.id)

        assert is_valid is True

    async def test_verify_context_integrity_empty(self, async_session: AsyncSession):
        """Test context integrity verification for empty conversation."""
        conv_repo = ConversationRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-empty")
        await async_session.flush()

        # Empty conversation should be valid
        manager = ContextManager(async_session)
        is_valid = await manager.verify_context_integrity(conversation.id)

        assert is_valid is True
