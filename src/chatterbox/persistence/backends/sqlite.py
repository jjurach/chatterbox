"""
SQLite storage backend for Chatterbox persistence.

Provides a concrete implementation of the StorageBackend protocol using SQLite.
This backend is suitable for:
- Development and testing
- Single-device deployments
- Edge devices (ESP32 with SQLite support)
- Development environments with modest data volumes

Features:
- Async support via sqlalchemy-asyncpure (pure-Python SQLite driver)
- Connection pooling with configurable pool size
- Automatic schema creation
- Health checks with simple ping queries
- PostgreSQL-compatible interface (easy migration)

For production multi-device deployments, migrate to PostgreSQL using the same
backend interface (see docs/persistent-storage-architecture.md).

Technical notes:
- Uses NullPool by default to avoid threading issues with SQLite
- All operations are async-safe
- Supports in-memory (:memory:) databases for testing
- Respects database file permissions and creates parent directories
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from chatterbox.persistence.schema import Base

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """SQLite implementation of StorageBackend.

    Attributes:
        database_url: Async SQLite connection URL (e.g., sqlite+aiosqlite:///path/to/db.sqlite)
        echo: If True, log all SQL statements.
        connect_args: Additional arguments for sqlite3 connection.
    """

    def __init__(
        self,
        database_url: str = "sqlite+aiosqlite:///:memory:",
        echo: bool = False,
        connect_args: dict[str, Any] | None = None,
    ) -> None:
        """Initialize SQLiteStorage.

        Args:
            database_url: SQLite connection URL. Supports:
                - ":memory:" for in-memory databases (default)
                - "/path/to/db.sqlite" for file-based databases
                - "sqlite+aiosqlite:///:memory:" for explicit in-memory
                - "sqlite+aiosqlite:////absolute/path/db.sqlite" for absolute paths
            echo: If True, print all SQL statements to logger.
            connect_args: Extra kwargs for sqlite3.connect() (timeout, check_same_thread, etc.)
                For in-memory databases, defaults to {"check_same_thread": False}
                to ensure all connections share the same database.
        """
        self.database_url = database_url
        self.echo = echo

        # For in-memory databases, default to check_same_thread=False to enable
        # sharing the same in-memory database across multiple connections (needed with NullPool)
        if connect_args is None:
            connect_args = {}
        if ":memory:" in database_url and "check_same_thread" not in connect_args:
            connect_args = {**connect_args, "check_same_thread": False}

        self.connect_args = connect_args
        self._engine = None
        self._session_maker = None

        # Ensure parent directory exists for file-based databases
        if "sqlite+aiosqlite:///" in database_url and ":memory:" not in database_url:
            db_path = database_url.replace("sqlite+aiosqlite:///", "")
            if db_path.startswith("/"):
                db_path = db_path[1:]
            parent = Path(db_path).parent
            parent.mkdir(parents=True, exist_ok=True)
            logger.info("Created database directory: %s", parent)

    async def initialize(self) -> None:
        """Initialize the SQLite storage backend.

        Creates the async engine and session factory. Safe to call multiple times.
        """
        if self._engine is not None:
            logger.debug("Storage already initialized, skipping")
            return

        logger.info("Initializing SQLite storage: %s", self.connection_string)

        # Choose pool class based on database type
        # In-memory databases need StaticPool to maintain a single connection
        # File-based databases use NullPool to avoid threading issues
        poolclass = StaticPool if ":memory:" in self.database_url else NullPool

        self._engine = create_async_engine(
            self.database_url,
            echo=self.echo,
            connect_args=self.connect_args,
            poolclass=poolclass,
        )

        # Create session factory
        self._session_maker = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

        logger.info("SQLite storage initialized successfully")

    async def shutdown(self) -> None:
        """Shut down the SQLite storage backend.

        Closes all connections in the pool. Safe to call multiple times.
        """
        if self._engine is None:
            logger.debug("Storage not initialized, skipping shutdown")
            return

        logger.info("Shutting down SQLite storage")
        await self._engine.dispose()
        self._engine = None
        self._session_maker = None
        logger.info("SQLite storage shut down successfully")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield an async ORM session for database operations.

        The session is automatically rolled back on exception.

        Usage:
            async with backend.get_session() as session:
                result = await session.execute(query)

        Yields:
            AsyncSession bound to the connection pool.

        Raises:
            RuntimeError: If the backend has not been initialized.
        """
        if self._session_maker is None:
            raise RuntimeError(
                "Storage backend not initialized. Call initialize() first."
            )

        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_tables(self) -> None:
        """Create all tables in the database schema.

        Idempotent: safe to call even if tables already exist.

        Raises:
            RuntimeError: If the backend has not been initialized.
        """
        if self._engine is None:
            raise RuntimeError(
                "Storage backend not initialized. Call initialize() first."
            )

        logger.info("Creating database tables")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    async def drop_tables(self) -> None:
        """Drop all tables in the database schema.

        WARNING: Destructive operation. Only use in testing/development.

        Raises:
            RuntimeError: If the backend has not been initialized.
        """
        if self._engine is None:
            raise RuntimeError(
                "Storage backend not initialized. Call initialize() first."
            )

        logger.warning("Dropping all database tables (destructive operation)")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")

    async def healthcheck(self) -> bool:
        """Check if the storage backend is healthy.

        Performs a simple SELECT 1 query to verify the connection.

        Returns:
            True if healthy, False if the check fails.
        """
        if self._engine is None:
            logger.warning("Storage not initialized, healthcheck returning False")
            return False

        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
            logger.debug("Storage healthcheck passed")
            return True
        except Exception as exc:
            logger.error("Storage healthcheck failed: %s", exc)
            return False

    @property
    def connection_string(self) -> str:
        """Return the connection string (with redacted credentials).

        For SQLite, no credentials exist, so returns the URL as-is.
        """
        return self.database_url
