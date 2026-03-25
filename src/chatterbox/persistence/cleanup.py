"""
Retention policy and cleanup service for conversation data.

Implements configurable TTL-based cleanup for messages, tool calls, and context
snapshots. Supports:
- Configurable retention periods per data type
- Dry-run mode for testing before actual deletion
- Background scheduled cleanup job
- Safety checks to prevent data loss
- Metrics and alerts

Reference: docs/epic5-context-persistence-proposal.md
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatterbox.persistence.schema import (
    Conversation,
    ContextSnapshot,
    Message,
    ToolCall,
)

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Configuration for data retention.

    Attributes:
        message_ttl_days: Keep messages for this many days (default: 30).
        tool_call_ttl_days: Keep tool calls for this many days (default: 30).
        snapshot_ttl_days: Keep context snapshots for this many days (default: 7).
        conversation_ttl_days: Keep empty conversations for this many days (default: 90).
            A conversation is considered "empty" if it has no recent messages.
        min_messages_per_conversation: Never delete conversations with fewer messages than this
            (safety check, default: 1).
    """

    message_ttl_days: int = 30
    tool_call_ttl_days: int = 30
    snapshot_ttl_days: int = 7
    conversation_ttl_days: int = 90
    min_messages_per_conversation: int = 1


@dataclass
class CleanupStats:
    """Statistics from a cleanup run.

    Attributes:
        messages_deleted: Number of messages removed.
        tool_calls_deleted: Number of tool calls removed.
        snapshots_deleted: Number of context snapshots removed.
        conversations_deleted: Number of empty conversations removed.
        total_deleted: Sum of all deletions.
        duration_ms: Time taken to run cleanup (milliseconds).
        errors: List of error messages encountered.
    """

    messages_deleted: int = 0
    tool_calls_deleted: int = 0
    snapshots_deleted: int = 0
    conversations_deleted: int = 0
    total_deleted: int = 0
    duration_ms: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class CleanupService:
    """Service for executing retention policies and cleaning up old data.

    Methods:
    - execute_cleanup: Run the cleanup job for all data types.
    - dry_run: Preview what would be deleted without actually deleting.
    - schedule_cleanup: Schedule periodic cleanup job (optional).
    """

    def __init__(self, session: AsyncSession, policy: Optional[RetentionPolicy] = None):
        """Initialize the cleanup service.

        Args:
            session: AsyncSession for database operations.
            policy: Retention policy (uses defaults if None).
        """
        self.session = session
        self.policy = policy or RetentionPolicy()

    async def execute_cleanup(self) -> CleanupStats:
        """Execute the retention policy cleanup job.

        Removes:
        - Messages older than message_ttl_days
        - Tool calls older than tool_call_ttl_days
        - Context snapshots older than snapshot_ttl_days
        - Empty conversations older than conversation_ttl_days (optional)

        Safety checks:
        - Never deletes the last N messages per conversation
        - Logs all deletions
        - Reports any errors

        Returns:
            CleanupStats with counts of deleted items.
        """
        stats = CleanupStats()
        start = datetime.utcnow()

        try:
            # Delete old messages
            logger.info(
                "Cleanup: Deleting messages older than %d days",
                self.policy.message_ttl_days,
            )
            messages_deleted = await self._delete_old_messages()
            stats.messages_deleted = messages_deleted

            # Delete old tool calls
            logger.info(
                "Cleanup: Deleting tool calls older than %d days",
                self.policy.tool_call_ttl_days,
            )
            tool_calls_deleted = await self._delete_old_tool_calls()
            stats.tool_calls_deleted = tool_calls_deleted

            # Delete old snapshots
            logger.info(
                "Cleanup: Deleting context snapshots older than %d days",
                self.policy.snapshot_ttl_days,
            )
            snapshots_deleted = await self._delete_old_snapshots()
            stats.snapshots_deleted = snapshots_deleted

            # Delete empty conversations (optional)
            logger.info(
                "Cleanup: Deleting empty conversations older than %d days",
                self.policy.conversation_ttl_days,
            )
            conversations_deleted = await self._delete_empty_conversations()
            stats.conversations_deleted = conversations_deleted

            stats.total_deleted = (
                messages_deleted
                + tool_calls_deleted
                + snapshots_deleted
                + conversations_deleted
            )

            # Commit the transaction
            await self.session.commit()
            logger.info(
                "Cleanup completed: %d messages, %d tool_calls, %d snapshots, %d conversations",
                messages_deleted,
                tool_calls_deleted,
                snapshots_deleted,
                conversations_deleted,
            )

        except Exception as e:
            if self.session is not None:
                await self.session.rollback()
            error_msg = f"Cleanup failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            stats.errors.append(error_msg)

        finally:
            end = datetime.utcnow()
            stats.duration_ms = int((end - start).total_seconds() * 1000)

        return stats

    async def dry_run(self) -> CleanupStats:
        """Preview what would be deleted without actually deleting.

        This is useful for testing cleanup policies before enabling automatic cleanup.
        Performs the same queries as execute_cleanup() but rolls back at the end.

        Returns:
            CleanupStats with counts of what would be deleted.
        """
        stats = CleanupStats()
        start = datetime.utcnow()

        try:
            # Count old messages
            cutoff_date = datetime.utcnow() - timedelta(days=self.policy.message_ttl_days)
            msg_result = await self.session.execute(
                select(Message).where(Message.created_at < cutoff_date)
            )
            messages = msg_result.scalars().all()
            stats.messages_deleted = len(messages)
            logger.info("Dry-run: Would delete %d old messages", len(messages))

            # Count old tool calls
            cutoff_date = datetime.utcnow() - timedelta(days=self.policy.tool_call_ttl_days)
            tc_result = await self.session.execute(
                select(ToolCall).where(ToolCall.created_at < cutoff_date)
            )
            tool_calls = tc_result.scalars().all()
            stats.tool_calls_deleted = len(tool_calls)
            logger.info("Dry-run: Would delete %d old tool calls", len(tool_calls))

            # Count old snapshots
            cutoff_date = datetime.utcnow() - timedelta(days=self.policy.snapshot_ttl_days)
            snap_result = await self.session.execute(
                select(ContextSnapshot).where(ContextSnapshot.created_at < cutoff_date)
            )
            snapshots = snap_result.scalars().all()
            stats.snapshots_deleted = len(snapshots)
            logger.info("Dry-run: Would delete %d old snapshots", len(snapshots))

            # Count empty conversations
            conversations_deleted = await self._count_empty_conversations()
            stats.conversations_deleted = conversations_deleted
            logger.info("Dry-run: Would delete %d empty conversations", conversations_deleted)

            stats.total_deleted = (
                stats.messages_deleted
                + stats.tool_calls_deleted
                + stats.snapshots_deleted
                + conversations_deleted
            )

        except Exception as e:
            error_msg = f"Dry-run failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            stats.errors.append(error_msg)

        finally:
            # Always rollback for dry-run
            await self.session.rollback()
            end = datetime.utcnow()
            stats.duration_ms = int((end - start).total_seconds() * 1000)

        return stats

    async def _delete_old_messages(self) -> int:
        """Delete messages older than message_ttl_days.

        Excludes the most recent min_messages_per_conversation per conversation.

        Returns:
            Number of messages deleted.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.message_ttl_days)

        # Get all conversations with their message counts
        conv_result = await self.session.execute(select(Conversation))
        conversations = conv_result.scalars().all()

        total_deleted = 0
        for conv in conversations:
            # Get the most recent messages for this conversation
            msg_result = await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .limit(self.policy.min_messages_per_conversation)
            )
            recent_messages = msg_result.scalars().all()
            recent_ids = {msg.id for msg in recent_messages}

            # Delete old messages, excluding recent ones
            delete_result = await self.session.execute(
                delete(Message).where(
                    and_(
                        Message.conversation_id == conv.id,
                        Message.created_at < cutoff_date,
                        Message.id.notin_(recent_ids),
                    )
                )
            )
            total_deleted += delete_result.rowcount or 0

        return total_deleted

    async def _delete_old_tool_calls(self) -> int:
        """Delete tool calls older than tool_call_ttl_days.

        Returns:
            Number of tool calls deleted.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.tool_call_ttl_days)
        delete_result = await self.session.execute(
            delete(ToolCall).where(ToolCall.created_at < cutoff_date)
        )
        return delete_result.rowcount or 0

    async def _delete_old_snapshots(self) -> int:
        """Delete context snapshots older than snapshot_ttl_days.

        Returns:
            Number of snapshots deleted.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.snapshot_ttl_days)
        delete_result = await self.session.execute(
            delete(ContextSnapshot).where(ContextSnapshot.created_at < cutoff_date)
        )
        return delete_result.rowcount or 0

    async def _delete_empty_conversations(self) -> int:
        """Delete empty conversations older than conversation_ttl_days.

        A conversation is "empty" if it has no messages created after the cutoff date.

        Returns:
            Number of conversations deleted.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.conversation_ttl_days)

        # Find conversations with no recent messages
        result = await self.session.execute(
            select(Conversation).where(Conversation.created_at < cutoff_date)
        )
        old_conversations = result.scalars().all()

        total_deleted = 0
        for conv in old_conversations:
            # Check if conversation has any recent messages
            msg_result = await self.session.execute(
                select(Message).where(Message.conversation_id == conv.id)
            )
            messages = msg_result.scalars().all()

            if len(messages) == 0:
                # Safe to delete empty conversation
                await self.session.delete(conv)
                total_deleted += 1

        return total_deleted

    async def _count_empty_conversations(self) -> int:
        """Count empty conversations that would be deleted.

        Returns:
            Number of empty conversations.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.conversation_ttl_days)

        result = await self.session.execute(
            select(Conversation).where(Conversation.created_at < cutoff_date)
        )
        old_conversations = result.scalars().all()

        count = 0
        for conv in old_conversations:
            msg_result = await self.session.execute(
                select(Message).where(Message.conversation_id == conv.id)
            )
            messages = msg_result.scalars().all()
            if len(messages) == 0:
                count += 1

        return count


class ScheduledCleanupJob:
    """Runs cleanup job at regular intervals.

    Usage:
        job = ScheduledCleanupJob(storage_backend, policy=RetentionPolicy())
        await job.start()  # Runs daily
        await job.stop()   # Graceful shutdown
    """

    def __init__(
        self,
        storage_backend,
        policy: Optional[RetentionPolicy] = None,
        interval_hours: int = 24,
    ):
        """Initialize the scheduled cleanup job.

        Args:
            storage_backend: SQLiteStorage or compatible backend.
            policy: Retention policy (uses defaults if None).
            interval_hours: Run cleanup every N hours (default: 24).
        """
        self.storage = storage_backend
        self.policy = policy or RetentionPolicy()
        self.interval_hours = interval_hours
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background cleanup job."""
        if self._running:
            logger.warning("Cleanup job already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Started scheduled cleanup job (interval: %d hours)",
            self.interval_hours,
        )

    async def stop(self) -> None:
        """Stop the background cleanup job gracefully."""
        if not self._running:
            logger.debug("Cleanup job not running")
            return

        self._running = False
        if self._task:
            await self._task
        logger.info("Stopped scheduled cleanup job")

    async def _run_loop(self) -> None:
        """Main loop for the background job."""
        while self._running:
            try:
                interval_seconds = self.interval_hours * 3600
                await asyncio.sleep(interval_seconds)

                if not self._running:
                    break

                async with self.storage.get_session() as session:
                    service = CleanupService(session, self.policy)
                    stats = await service.execute_cleanup()

                    if stats.has_errors:
                        logger.warning(
                            "Cleanup job completed with errors: %s",
                            stats.errors,
                        )
                    else:
                        logger.info(
                            "Cleanup job completed successfully: %d items deleted in %dms",
                            stats.total_deleted,
                            stats.duration_ms,
                        )

            except Exception as e:
                logger.error("Cleanup job error: %s", str(e), exc_info=True)
