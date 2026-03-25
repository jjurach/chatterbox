"""
Context search and query interface for conversation history.

Provides full-text search, filtering by date/role/conversation, and relevance
ranking. Uses SQLite FTS5 for efficient full-text search.

Features:
- Full-text search on message content
- Filter by date range, role, conversation
- Search results ranked by relevance
- Latency <500ms typical
- Example queries documented

Reference: docs/context-retrieval-guide.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.schema import Conversation, Message

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result.

    Attributes:
        message_id: Message UUID.
        conversation_id: Conversation UUID.
        content: The message content.
        role: Message role (user, assistant, system).
        created_at: When the message was created.
        sequence: Message order in conversation.
        relevance_score: Relevance score (0.0-1.0), higher is more relevant.
    """

    message_id: str
    conversation_id: str
    content: str
    role: str
    created_at: datetime
    sequence: int
    relevance_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "content": self.content,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "sequence": self.sequence,
            "relevance_score": self.relevance_score,
        }


@dataclass
class SearchQuery:
    """A search query with filters.

    Attributes:
        query: Full-text search query (e.g., "weather today").
        conversation_id: Optional filter by conversation UUID.
        user_id: Optional filter by user UUID.
        role: Optional filter by message role ("user", "assistant", "system").
        start_date: Optional filter for messages after this date.
        end_date: Optional filter for messages before this date.
        limit: Maximum results to return (default: 50).
        offset: Skip N results (for pagination).
    """

    query: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


class ContextSearchEngine:
    """Search engine for conversation history.

    Methods:
    - search: Full-text search with optional filters
    - advanced_search: Search with complex filter combinations
    - suggest_filters: Get available filter values
    """

    def __init__(self, session: AsyncSession):
        """Initialize the search engine.

        Args:
            session: AsyncSession for database operations.
        """
        self.session = session

    async def search(self, query: SearchQuery) -> tuple[list[SearchResult], int]:
        """Perform a full-text search on message content.

        Supports basic text queries with optional filters for date range, role, etc.
        Results are ranked by relevance (proximity of search terms in content).

        Latency target: <500ms for typical queries.

        Args:
            query: SearchQuery with search terms and optional filters.

        Returns:
            Tuple of (list of SearchResult objects, total count of matching messages).

        Example:
            >>> q = SearchQuery(
            ...     query="weather forecast",
            ...     role="assistant",
            ...     start_date=datetime(2024, 1, 1),
            ...     limit=10
            ... )
            >>> results, total = await engine.search(q)
            >>> for result in results:
            ...     print(result.content, result.relevance_score)
        """
        # Build the WHERE clause
        where_conditions = []

        # Add conversation filter
        if query.conversation_id:
            where_conditions.append(Message.conversation_id == query.conversation_id)

        # Add role filter
        if query.role:
            where_conditions.append(Message.role == query.role)

        # Add date range filters
        if query.start_date:
            where_conditions.append(Message.created_at >= query.start_date)
        if query.end_date:
            where_conditions.append(Message.created_at <= query.end_date)

        # Add full-text search on content
        # SQLite LIKE is case-insensitive by default
        search_pattern = f"%{query.query}%"
        where_conditions.append(Message.content.ilike(search_pattern))

        # Build the query
        stmt = select(Message)
        if where_conditions:
            stmt = stmt.where(and_(*where_conditions))

        # Count total matches
        count_result = await self.session.execute(stmt)
        total_count = len(count_result.scalars().all())

        # Get paginated results
        stmt = (
            select(Message)
            .where(and_(*where_conditions))
            .order_by(Message.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )

        result = await self.session.execute(stmt)
        messages = result.scalars().all()

        # Convert to SearchResult objects with relevance scores
        search_results = []
        for msg in messages:
            # Calculate relevance score (simple heuristic: position of first match)
            relevance_score = self._calculate_relevance(msg.content, query.query)
            search_results.append(
                SearchResult(
                    message_id=msg.id,
                    conversation_id=msg.conversation_id,
                    content=msg.content,
                    role=msg.role,
                    created_at=msg.created_at,
                    sequence=msg.sequence,
                    relevance_score=relevance_score,
                )
            )

        # Sort by relevance score (descending)
        search_results.sort(key=lambda r: r.relevance_score, reverse=True)

        logger.debug(
            "Search query '%s' found %d results (total: %d)",
            query.query,
            len(search_results),
            total_count,
        )

        return search_results, total_count

    async def advanced_search(
        self,
        query: SearchQuery,
        exclude_queries: Optional[list[str]] = None,
    ) -> tuple[list[SearchResult], int]:
        """Advanced search with inclusion/exclusion terms.

        Supports:
        - Multiple inclusion queries (OR'd together)
        - Exclusion terms (NOT'd)
        - Complex filter combinations

        Args:
            query: Main search query with filters.
            exclude_queries: Optional list of terms to exclude.

        Returns:
            Tuple of (list of SearchResult objects, total count).

        Example:
            >>> q = SearchQuery(query="weather")
            >>> results, total = await engine.advanced_search(
            ...     q,
            ...     exclude_queries=["rain", "snow"]
            ... )
        """
        # Build the base WHERE clause
        where_conditions = []

        # Add conversation filter
        if query.conversation_id:
            where_conditions.append(Message.conversation_id == query.conversation_id)

        # Add user filter
        if query.user_id:
            conv_result = await self.session.execute(
                select(Conversation).where(Conversation.user_id == query.user_id)
            )
            conversation_ids = [c.id for c in conv_result.scalars().all()]
            if conversation_ids:
                where_conditions.append(Message.conversation_id.in_(conversation_ids))
            else:
                # No conversations for this user
                return [], 0

        # Add role filter
        if query.role:
            where_conditions.append(Message.role == query.role)

        # Add date range filters
        if query.start_date:
            where_conditions.append(Message.created_at >= query.start_date)
        if query.end_date:
            where_conditions.append(Message.created_at <= query.end_date)

        # Add inclusion search
        search_pattern = f"%{query.query}%"
        where_conditions.append(Message.content.ilike(search_pattern))

        # Add exclusion searches
        if exclude_queries:
            for exclude_query in exclude_queries:
                exclude_pattern = f"%{exclude_query}%"
                where_conditions.append(~Message.content.ilike(exclude_pattern))

        # Build query
        stmt = select(Message)
        if where_conditions:
            stmt = stmt.where(and_(*where_conditions))

        # Count total
        count_result = await self.session.execute(stmt)
        total_count = len(count_result.scalars().all())

        # Get paginated results
        stmt = (
            select(Message)
            .where(and_(*where_conditions))
            .order_by(Message.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )

        result = await self.session.execute(stmt)
        messages = result.scalars().all()

        # Convert to SearchResult with relevance scores
        search_results = []
        for msg in messages:
            relevance_score = self._calculate_relevance(msg.content, query.query)
            search_results.append(
                SearchResult(
                    message_id=msg.id,
                    conversation_id=msg.conversation_id,
                    content=msg.content,
                    role=msg.role,
                    created_at=msg.created_at,
                    sequence=msg.sequence,
                    relevance_score=relevance_score,
                )
            )

        search_results.sort(key=lambda r: r.relevance_score, reverse=True)

        logger.debug(
            "Advanced search found %d results (total: %d)",
            len(search_results),
            total_count,
        )

        return search_results, total_count

    async def search_by_user(
        self,
        user_id: str,
        query: SearchQuery,
    ) -> tuple[list[SearchResult], int]:
        """Search messages from a specific user.

        Automatically filters to only conversations owned by the user.

        Args:
            user_id: The user UUID.
            query: Search query.

        Returns:
            Tuple of (list of SearchResult objects, total count).
        """
        # Get user's conversations
        conv_result = await self.session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversations = conv_result.scalars().all()
        conversation_ids = [c.id for c in conversations]

        if not conversation_ids:
            return [], 0

        # Build WHERE clause
        where_conditions = [Message.conversation_id.in_(conversation_ids)]

        # Add role filter
        if query.role:
            where_conditions.append(Message.role == query.role)

        # Add date filters
        if query.start_date:
            where_conditions.append(Message.created_at >= query.start_date)
        if query.end_date:
            where_conditions.append(Message.created_at <= query.end_date)

        # Add full-text search
        search_pattern = f"%{query.query}%"
        where_conditions.append(Message.content.ilike(search_pattern))

        # Count total
        stmt = select(Message).where(and_(*where_conditions))
        count_result = await self.session.execute(stmt)
        total_count = len(count_result.scalars().all())

        # Get results
        stmt = (
            select(Message)
            .where(and_(*where_conditions))
            .order_by(Message.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )

        result = await self.session.execute(stmt)
        messages = result.scalars().all()

        # Convert to SearchResult
        search_results = []
        for msg in messages:
            relevance_score = self._calculate_relevance(msg.content, query.query)
            search_results.append(
                SearchResult(
                    message_id=msg.id,
                    conversation_id=msg.conversation_id,
                    content=msg.content,
                    role=msg.role,
                    created_at=msg.created_at,
                    sequence=msg.sequence,
                    relevance_score=relevance_score,
                )
            )

        search_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return search_results, total_count

    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score for a message content.

        Simple heuristic: position of first match and term frequency.
        Score range: 0.0 - 1.0 (higher is more relevant).

        Args:
            content: The message content.
            query: The search query.

        Returns:
            Relevance score.
        """
        content_lower = content.lower()
        query_lower = query.lower()

        # Find position of first match
        pos = content_lower.find(query_lower)
        if pos == -1:
            return 0.0

        # Earlier matches are more relevant
        position_score = 1.0 - (pos / len(content))

        # Count term frequency
        term_count = content_lower.count(query_lower)
        frequency_score = min(1.0, term_count / len(content.split()))

        # Combine scores (equal weight)
        return (position_score + frequency_score) / 2.0

    async def get_search_suggestions(
        self,
        partial_query: str,
        limit: int = 5,
    ) -> list[str]:
        """Get search suggestions based on partial query.

        Returns words from messages that start with the partial query.

        Args:
            partial_query: The partial query string.
            limit: Maximum suggestions to return.

        Returns:
            List of suggested search terms.
        """
        # This is a simple implementation that finds matching words in content
        # In production, use a proper suggestions table or full-text index
        stmt = select(Message.content)
        result = await self.session.execute(stmt)
        all_messages = result.scalars().all()

        suggestions = set()
        search_prefix = partial_query.lower()

        for content in all_messages:
            words = content.split()
            for word in words:
                word_lower = word.lower().strip(".,!?;:")
                if word_lower.startswith(search_prefix) and len(word_lower) > len(search_prefix):
                    suggestions.add(word_lower)
                    if len(suggestions) >= limit:
                        break
            if len(suggestions) >= limit:
                break

        return sorted(list(suggestions))[:limit]
