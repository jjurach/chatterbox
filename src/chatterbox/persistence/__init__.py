"""
Persistence layer for Chatterbox conversation storage.

This module provides a pluggable storage abstraction for persisting conversations,
messages, tool calls, and context snapshots to various backends (SQLite, PostgreSQL, etc.).

Epic 5 Phase 1: Storage & ORM Layer
- Task 5.1: Backend Evaluation
- Task 5.2: Storage Schema Design
- Task 5.3: SQLAlchemy ORM Models

Epic 5 Phase 3: LLM Framework Integration
- Task 5.9: ConversationManager bridging Epic 4 and persistence
- Task 5.10: Comprehensive testing and validation
"""

from chatterbox.persistence.backends.base import StorageBackend
from chatterbox.persistence.backends.sqlite import SQLiteStorage
from chatterbox.persistence.conversation_manager import ConversationManager
from chatterbox.persistence.repositories import (
    ConversationRepository,
    ContextSnapshotRepository,
    MessageRepository,
    ToolCallRepository,
    UserRepository,
)

__all__ = [
    # Backend
    "StorageBackend",
    "SQLiteStorage",
    # Manager (Epic 5.9)
    "ConversationManager",
    # Repositories
    "UserRepository",
    "ConversationRepository",
    "MessageRepository",
    "ToolCallRepository",
    "ContextSnapshotRepository",
]
