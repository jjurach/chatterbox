"""
Tests for context search and query interface.

Tests cover:
- Basic full-text search
- Search with filters (date, role, conversation)
- Advanced search with exclusions
- Result ranking and relevance
- Search suggestions
- User-scoped search
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.search import (
    ContextSearchEngine,
    SearchQuery,
    SearchResult,
)
from chatterbox.persistence.repositories import (
    ConversationRepository,
    MessageRepository,
    UserRepository,
)


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_create_search_query(self):
        """Test creating a search query."""
        query = SearchQuery(
            query="weather",
            conversation_id="conv-1",
            role="assistant",
            limit=25,
        )
        assert query.query == "weather"
        assert query.conversation_id == "conv-1"
        assert query.role == "assistant"
        assert query.limit == 25

    def test_search_query_defaults(self):
        """Test default values in SearchQuery."""
        query = SearchQuery(query="test")
        assert query.query == "test"
        assert query.conversation_id is None
        assert query.user_id is None
        assert query.role is None
        assert query.limit == 50
        assert query.offset == 0


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating a search result."""
        result = SearchResult(
            message_id="msg-1",
            conversation_id="conv-1",
            content="The weather is nice",
            role="assistant",
            created_at=datetime.utcnow(),
            sequence=5,
            relevance_score=0.85,
        )
        assert result.message_id == "msg-1"
        assert result.conversation_id == "conv-1"
        assert result.role == "assistant"
        assert result.relevance_score == 0.85

    def test_search_result_to_dict(self):
        """Test converting search result to dict."""
        now = datetime.utcnow()
        result = SearchResult(
            message_id="msg-1",
            conversation_id="conv-1",
            content="Test content",
            role="user",
            created_at=now,
            sequence=1,
            relevance_score=0.75,
        )
        result_dict = result.to_dict()

        assert result_dict["message_id"] == "msg-1"
        assert result_dict["role"] == "user"
        assert result_dict["relevance_score"] == 0.75


@pytest.mark.anyio
class TestContextSearchEngine:
    """Tests for ContextSearchEngine search operations."""

    async def test_basic_search(self, async_session: AsyncSession):
        """Test basic full-text search."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-1")

        # Add messages
        await msg_repo.add(conversation.id, "user", "What is the weather today?")
        await msg_repo.add(conversation.id, "assistant", "The weather is sunny")
        await msg_repo.add(conversation.id, "user", "Thanks for the info")

        await async_session.flush()

        # Search for "weather"
        engine = ContextSearchEngine(async_session)
        query = SearchQuery(query="weather")
        results, total = await engine.search(query)

        assert len(results) >= 1
        assert total >= 1
        # At least one result should contain "weather"
        assert any("weather" in r.content.lower() for r in results)

    async def test_search_with_role_filter(self, async_session: AsyncSession):
        """Test search with role filter."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-2")

        # Add messages with different roles
        await msg_repo.add(conversation.id, "user", "user message")
        await msg_repo.add(conversation.id, "assistant", "assistant message")
        await msg_repo.add(conversation.id, "system", "system message")

        await async_session.flush()

        # Search for "message" but only assistant role
        engine = ContextSearchEngine(async_session)
        query = SearchQuery(query="message", role="assistant")
        results, total = await engine.search(query)

        assert len(results) >= 1
        # All results should be from assistant
        assert all(r.role == "assistant" for r in results)

    async def test_search_with_date_range(self, async_session: AsyncSession):
        """Test search with date range filter."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-3")

        # Add message
        msg = await msg_repo.add(conversation.id, "user", "dated message")
        msg.created_at = datetime.utcnow()

        await async_session.flush()

        # Search within date range
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        engine = ContextSearchEngine(async_session)
        query = SearchQuery(
            query="dated",
            start_date=yesterday,
            end_date=tomorrow,
        )
        results, total = await engine.search(query)

        assert len(results) >= 1

    async def test_search_no_matches(self, async_session: AsyncSession):
        """Test search with no matches."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-4")
        await msg_repo.add(conversation.id, "user", "hello world")

        await async_session.flush()

        # Search for non-existent term
        engine = ContextSearchEngine(async_session)
        query = SearchQuery(query="xyzabc123")
        results, total = await engine.search(query)

        assert len(results) == 0
        assert total == 0

    async def test_advanced_search_with_exclusions(self, async_session: AsyncSession):
        """Test advanced search with exclusion terms."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-5")

        # Add messages
        await msg_repo.add(conversation.id, "user", "I like sunny weather")
        await msg_repo.add(conversation.id, "user", "I dislike rainy weather")
        await msg_repo.add(conversation.id, "assistant", "weather forecast available")

        await async_session.flush()

        # Search for "weather" but exclude "rainy"
        engine = ContextSearchEngine(async_session)
        query = SearchQuery(query="weather")
        results, total = await engine.advanced_search(query, exclude_queries=["rainy"])

        assert len(results) >= 1
        # Results should not contain "rainy"
        assert all("rainy" not in r.content.lower() for r in results)

    async def test_search_user_context(self, async_session: AsyncSession):
        """Test search filtered by user."""
        user_repo = UserRepository(async_session)
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        # Create two users
        user1 = await user_repo.create("user1")
        user2 = await user_repo.create("user2")

        # Create conversations for each user
        conv1 = await conv_repo.create(user_id=user1.id, conversation_id="conv-user1")
        conv2 = await conv_repo.create(user_id=user2.id, conversation_id="conv-user2")

        # Add messages to each conversation
        await msg_repo.add(conv1.id, "user", "user1 message")
        await msg_repo.add(conv2.id, "user", "user2 message")

        await async_session.flush()

        # Search for user1
        engine = ContextSearchEngine(async_session)
        query = SearchQuery(query="message")
        results, total = await engine.search_by_user(user1.id, query)

        assert len(results) >= 1
        # All results should be from user1's conversation
        assert all(r.conversation_id == conv1.id for r in results)

    async def test_search_pagination(self, async_session: AsyncSession):
        """Test search pagination."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-6")

        # Add many messages with same content
        for i in range(20):
            await msg_repo.add(conversation.id, "user", f"test message {i}")

        await async_session.flush()

        # Search with pagination
        engine = ContextSearchEngine(async_session)
        query = SearchQuery(query="test", limit=5)

        # Get first page
        results1, total = await engine.search(query)
        assert len(results1) <= 5
        assert total >= 5

        # Get second page
        query.offset = 5
        results2, total = await engine.search(query)
        assert len(results2) <= 5

        # Ensure different results
        ids1 = {r.message_id for r in results1}
        ids2 = {r.message_id for r in results2}
        assert len(ids1 & ids2) == 0  # No overlap

    async def test_search_relevance_scoring(self, async_session: AsyncSession):
        """Test that results are ranked by relevance."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-7")

        # Add messages with varying relevance
        await msg_repo.add(conversation.id, "user", "weather weather weather")
        await msg_repo.add(conversation.id, "user", "I wonder about weather")
        await msg_repo.add(conversation.id, "user", "the weather is important")

        await async_session.flush()

        # Search for "weather"
        engine = ContextSearchEngine(async_session)
        query = SearchQuery(query="weather")
        results, total = await engine.search(query)

        assert len(results) >= 1
        # First result should have highest relevance
        if len(results) > 1:
            assert results[0].relevance_score >= results[1].relevance_score

    async def test_get_search_suggestions(self, async_session: AsyncSession):
        """Test search suggestions."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-8")

        # Add messages with various words
        await msg_repo.add(conversation.id, "user", "weather forecast sunshine")
        await msg_repo.add(conversation.id, "user", "when will it rain")
        await msg_repo.add(conversation.id, "assistant", "warm and windy conditions")

        await async_session.flush()

        # Get suggestions for "w"
        engine = ContextSearchEngine(async_session)
        suggestions = await engine.get_search_suggestions("w", limit=5)

        assert len(suggestions) >= 1
        # All suggestions should start with "w"
        assert all(s.startswith("w") for s in suggestions)

    async def test_search_case_insensitive(self, async_session: AsyncSession):
        """Test that search is case-insensitive."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-9")

        # Add message with mixed case
        await msg_repo.add(conversation.id, "user", "WEATHER is IMPORTANT")

        await async_session.flush()

        # Search with different cases
        engine = ContextSearchEngine(async_session)

        query1 = SearchQuery(query="weather")
        results1, _ = await engine.search(query1)

        query2 = SearchQuery(query="WEATHER")
        results2, _ = await engine.search(query2)

        # Should find the same results regardless of case
        assert len(results1) == len(results2)
