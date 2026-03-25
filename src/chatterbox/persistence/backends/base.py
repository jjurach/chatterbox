"""
Storage abstraction layer for Chatterbox persistence.

Defines a Protocol-based interface for storage backends, allowing pluggable
implementations (SQLite, PostgreSQL, etc.) without coupling the application
logic to a specific database.

The StorageBackend protocol defines operations for:
- Connection management (initialize, shutdown)
- Session creation (for ORM operations)
- Schema creation and migration
- Health checks

This design enables:
1. Easy testing with in-memory SQLite
2. Migration from SQLite to PostgreSQL without application changes
3. Support for multiple simultaneous backends (read replicas, etc.)
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends in Chatterbox persistence.

    Any class implementing this protocol can serve as a storage backend.
    The default implementation is `SQLiteStorage`.

    This Protocol enables pluggable backends:
    - SQLite for development and single-device deployments
    - PostgreSQL for multi-device and cloud deployments
    - In-memory backends for testing
    """

    async def initialize(self) -> None:
        """Initialize the storage backend.

        Creates connection pools, initializes the database, and runs
        migrations if needed. Safe to call multiple times.

        This method should be called during application startup.

        Raises:
            Exception: If initialization fails (connection error, migration failure, etc.)
        """
        ...

    async def shutdown(self) -> None:
        """Shut down the storage backend gracefully.

        Closes connection pools and releases resources. Safe to call
        multiple times and even if initialize() was never called.

        This method should be called during application shutdown.
        """
        ...

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield an async ORM session for database operations.

        The session is automatically committed or rolled back depending on
        whether an exception occurs. Use as a context manager or async iterator:

            async with backend.get_session() as session:
                result = await session.execute(query)

        The session is thread-safe and handles connection pooling transparently.

        Yields:
            An AsyncSession bound to the connection pool.

        Raises:
            Exception: If a session cannot be created (connection pool exhausted, etc.)
        """
        ...

    async def create_tables(self) -> None:
        """Create all tables in the database schema.

        Idempotent: safe to call even if tables already exist.
        Uses SQLAlchemy metadata to create tables based on ORM models.

        In a production environment, you would typically use Alembic for
        migrations instead. This method is useful for:
        - Development and testing
        - Initial setup for new deployments
        - In-memory test databases

        Raises:
            Exception: If table creation fails (e.g., permission denied).
        """
        ...

    async def drop_tables(self) -> None:
        """Drop all tables in the database schema.

        WARNING: This is a destructive operation that deletes all data.
        Only use in development/testing.

        Useful for:
        - Cleaning up test databases
        - Resetting development environments
        - Database reset during disaster recovery

        Raises:
            Exception: If table deletion fails (e.g., permission denied).
        """
        ...

    async def healthcheck(self) -> bool:
        """Check if the storage backend is healthy and accessible.

        Performs a simple database ping (e.g., SELECT 1) to verify:
        - Connection to the database is alive
        - Database is responding to queries
        - Credentials are still valid

        Returns:
            True if the backend is healthy, False otherwise.

        Raises:
            Exception: If the health check itself fails critically
                (e.g., credentials expired).
        """
        ...

    @property
    def connection_string(self) -> str:
        """Return the database connection string for logging/debugging.

        Should mask sensitive information (passwords, API keys, etc.)
        from the return value.

        Returns:
            A connection string suitable for logging (credentials redacted).
        """
        ...
