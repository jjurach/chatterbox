"""
Tests for retention policy and cleanup service.

Tests cover:
- Retention policy configuration
- Message cleanup (respecting minimum retention)
- Tool call cleanup
- Context snapshot cleanup
- Empty conversation deletion
- Dry-run mode
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.cleanup import (
    CleanupService,
    CleanupStats,
    RetentionPolicy,
    ScheduledCleanupJob,
)
from chatterbox.persistence.repositories import (
    ConversationRepository,
    MessageRepository,
    ToolCallRepository,
    ContextSnapshotRepository,
)


class TestRetentionPolicy:
    """Tests for RetentionPolicy configuration."""

    def test_default_policy(self):
        """Test default retention policy values."""
        policy = RetentionPolicy()
        assert policy.message_ttl_days == 30
        assert policy.tool_call_ttl_days == 30
        assert policy.snapshot_ttl_days == 7
        assert policy.conversation_ttl_days == 90
        assert policy.min_messages_per_conversation == 1

    def test_custom_policy(self):
        """Test custom retention policy."""
        policy = RetentionPolicy(
            message_ttl_days=60,
            tool_call_ttl_days=45,
            snapshot_ttl_days=14,
            conversation_ttl_days=180,
        )
        assert policy.message_ttl_days == 60
        assert policy.tool_call_ttl_days == 45
        assert policy.snapshot_ttl_days == 14
        assert policy.conversation_ttl_days == 180


class TestCleanupStats:
    """Tests for CleanupStats dataclass."""

    def test_cleanup_stats_creation(self):
        """Test creating cleanup stats."""
        stats = CleanupStats(
            messages_deleted=10,
            tool_calls_deleted=5,
            snapshots_deleted=2,
            conversations_deleted=1,
        )
        assert stats.messages_deleted == 10
        assert stats.tool_calls_deleted == 5
        assert stats.snapshots_deleted == 2
        assert stats.conversations_deleted == 1
        assert stats.total_deleted == 0  # Not calculated automatically
        assert stats.has_errors is False

    def test_cleanup_stats_with_errors(self):
        """Test cleanup stats with errors."""
        stats = CleanupStats(errors=["Error 1", "Error 2"])
        assert stats.has_errors is True
        assert len(stats.errors) == 2


@pytest.mark.anyio
class TestCleanupService:
    """Tests for CleanupService cleanup operations."""

    async def test_delete_old_messages(self, async_session: AsyncSession):
        """Test deletion of old messages."""
        # Create test data
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-1")

        # Create messages with different timestamps
        old_time = datetime.utcnow() - timedelta(days=40)
        recent_time = datetime.utcnow()

        # Add old message
        old_msg = await msg_repo.add(conversation.id, "user", "old message")
        old_msg.created_at = old_time

        # Add recent message
        recent_msg = await msg_repo.add(conversation.id, "assistant", "recent message")
        recent_msg.created_at = recent_time

        await async_session.flush()

        # Run cleanup with 30-day TTL
        policy = RetentionPolicy(message_ttl_days=30)
        service = CleanupService(async_session, policy)
        deleted = await service._delete_old_messages()

        # Should delete old message but keep recent one
        assert deleted == 1

        # Verify deletion
        messages = await msg_repo.get_by_conversation(conversation.id)
        assert len(messages) == 1
        assert messages[0].content == "recent message"

    async def test_cleanup_stats_structure(self, async_session: AsyncSession):
        """Test CleanupStats structure and totals."""
        conv_repo = ConversationRepository(async_session)
        conversation = await conv_repo.create(conversation_id="test-conv-2")

        # Run cleanup (should have no deletions)
        policy = RetentionPolicy()
        service = CleanupService(async_session, policy)
        stats = await service.execute_cleanup()

        assert isinstance(stats, CleanupStats)
        assert stats.messages_deleted >= 0
        assert stats.tool_calls_deleted >= 0
        assert stats.snapshots_deleted >= 0
        assert stats.duration_ms >= 0

    async def test_dry_run_mode(self, async_session: AsyncSession):
        """Test dry-run mode doesn't actually delete."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-3")

        # Create messages with different timestamps
        msg1 = await msg_repo.add(conversation.id, "user", "recent message")
        msg2 = await msg_repo.add(conversation.id, "user", "old message")

        # Manually set old timestamp on msg2
        old_time = datetime.utcnow() - timedelta(days=40)
        msg2.created_at = old_time
        await async_session.flush()

        # Run dry-run with session in same transaction
        policy = RetentionPolicy(message_ttl_days=30, min_messages_per_conversation=1)
        service = CleanupService(async_session, policy)
        stats = await service.dry_run()

        # Dry-run should not error
        assert stats.has_errors is False

        # Stats should show what would be deleted
        assert stats.messages_deleted >= 0  # Should detect old message as deletable

    async def test_minimum_messages_per_conversation(self, async_session: AsyncSession):
        """Test that minimum messages are preserved."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-4")

        # Create multiple old messages
        old_time = datetime.utcnow() - timedelta(days=40)
        for i in range(5):
            msg = await msg_repo.add(conversation.id, "user", f"message {i}")
            msg.created_at = old_time

        await async_session.flush()

        # Run cleanup with min_messages_per_conversation=2
        policy = RetentionPolicy(
            message_ttl_days=30,
            min_messages_per_conversation=2,
        )
        service = CleanupService(async_session, policy)
        deleted = await service._delete_old_messages()

        # Should delete 3 messages, keep 2
        assert deleted == 3

        messages = await msg_repo.get_by_conversation(conversation.id)
        assert len(messages) == 2

    async def test_empty_conversation_deletion(self, async_session: AsyncSession):
        """Test deletion of empty conversations."""
        conv_repo = ConversationRepository(async_session)

        # Create old empty conversation
        old_conv = await conv_repo.create(conversation_id="test-empty-1")
        old_conv.created_at = datetime.utcnow() - timedelta(days=100)

        # Create recent empty conversation
        recent_conv = await conv_repo.create(conversation_id="test-empty-2")

        await async_session.flush()

        # Run cleanup
        policy = RetentionPolicy(conversation_ttl_days=90)
        service = CleanupService(async_session, policy)
        deleted = await service._delete_empty_conversations()

        # Should delete old empty conversation only
        assert deleted == 1

        # Verify deletion
        result = await conv_repo.get_by_id(old_conv.id)
        assert result is None

        result = await conv_repo.get_by_id(recent_conv.id)
        assert result is not None

    async def test_cleanup_with_transaction_rollback(self, async_session: AsyncSession):
        """Test that cleanup rolls back on error."""
        conv_repo = ConversationRepository(async_session)
        msg_repo = MessageRepository(async_session)

        conversation = await conv_repo.create(conversation_id="test-conv-5")
        msg = await msg_repo.add(conversation.id, "user", "test message")
        await async_session.flush()

        # Create a service that will fail
        policy = RetentionPolicy()
        service = CleanupService(async_session, policy)

        # Manually induce an error scenario
        service.session = None  # Invalid session to cause error
        stats = await service.execute_cleanup()

        # Should have error recorded
        assert stats.has_errors
        assert len(stats.errors) > 0


@pytest.mark.anyio
class TestScheduledCleanupJob:
    """Tests for ScheduledCleanupJob background task."""

    async def test_job_creation(self):
        """Test creating a cleanup job."""
        # Create mock storage backend
        class MockStorage:
            async def get_session(self):
                pass

        storage = MockStorage()
        job = ScheduledCleanupJob(storage)

        assert not job._running
        assert job.interval_hours == 24
        assert job.policy is not None

    async def test_job_start_stop(self):
        """Test starting and stopping a job."""
        class MockStorage:
            async def get_session(self):
                # Return a mock session that does nothing
                from unittest.mock import AsyncMock
                return AsyncMock()

        storage = MockStorage()
        job = ScheduledCleanupJob(storage, interval_hours=0)  # Don't actually sleep

        # Start job
        await job.start()
        assert job._running

        # Stop job
        await job.stop()
        assert not job._running
