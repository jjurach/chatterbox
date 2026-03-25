"""Tests for SQLite storage backend implementation."""

import pytest
import pytest_asyncio

from chatterbox.persistence.backends.sqlite import SQLiteStorage


@pytest_asyncio.fixture
async def storage():
    """Create an in-memory SQLite storage for testing."""
    store = SQLiteStorage(
        database_url="sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    await store.initialize()
    yield store
    await store.shutdown()


@pytest_asyncio.fixture
async def storage_with_tables(storage):
    """Storage with tables created."""
    await storage.create_tables()
    return storage


class TestSQLiteStorageInitialization:
    """Tests for storage initialization and shutdown."""

    @pytest.mark.anyio
    async def test_initialize(self):
        """Test storage initialization."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        assert storage._engine is None
        assert storage._session_maker is None

        await storage.initialize()
        assert storage._engine is not None
        assert storage._session_maker is not None

        await storage.shutdown()

    @pytest.mark.anyio
    async def test_initialize_idempotent(self):
        """Test that initialize can be called multiple times."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        await storage.initialize()
        engine1 = storage._engine

        await storage.initialize()
        engine2 = storage._engine

        # Should return early and not create a new engine
        assert engine1 is engine2
        await storage.shutdown()

    @pytest.mark.anyio
    async def test_shutdown_idempotent(self, storage):
        """Test that shutdown can be called multiple times."""
        await storage.shutdown()
        await storage.shutdown()  # Should not raise

    @pytest.mark.anyio
    async def test_shutdown_without_initialize(self):
        """Test shutdown without prior initialization."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        await storage.shutdown()  # Should not raise


class TestSQLiteStorageSession:
    """Tests for session creation and usage."""

    @pytest.mark.anyio
    async def test_get_session(self, storage):
        """Test getting a session."""
        async with storage.get_session() as session:
            assert session is not None
            # Session should be usable for queries

    @pytest.mark.anyio
    async def test_get_session_without_initialize(self):
        """Test get_session raises if not initialized."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            async with storage.get_session() as session:
                pass

    @pytest.mark.anyio
    async def test_multiple_sessions(self, storage):
        """Test that multiple sessions can be created."""
        async with storage.get_session() as session1:
            assert session1 is not None

        async with storage.get_session() as session2:
            assert session2 is not None
            # Different sessions (not pooled for SQLite)
            assert session1 is not session2


class TestSQLiteStorageTables:
    """Tests for table creation and management."""

    @pytest.mark.anyio
    async def test_create_tables(self, storage):
        """Test creating tables."""
        await storage.create_tables()
        # Verify tables were created by checking metadata
        from chatterbox.persistence.schema import Base

        expected_tables = {
            "users",
            "conversations",
            "messages",
            "tool_calls",
            "context_snapshots",
        }
        assert all(table in Base.metadata.tables for table in expected_tables)

    @pytest.mark.anyio
    async def test_create_tables_idempotent(self, storage):
        """Test that create_tables is idempotent."""
        await storage.create_tables()
        await storage.create_tables()  # Should not raise

    @pytest.mark.anyio
    async def test_create_tables_without_initialize(self):
        """Test create_tables raises if not initialized."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            await storage.create_tables()

    @pytest.mark.anyio
    async def test_drop_tables(self, storage_with_tables):
        """Test dropping tables."""
        # Add some data first
        async with storage_with_tables.get_session() as session:
            from chatterbox.persistence.schema import User

            user = User(id="123", username="testuser")
            session.add(user)

        # Drop tables
        await storage_with_tables.drop_tables()

        # Verify tables are gone (try to create them again to confirm)
        await storage_with_tables.create_tables()  # Should work

    @pytest.mark.anyio
    async def test_drop_tables_without_initialize(self):
        """Test drop_tables raises if not initialized."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            await storage.drop_tables()


class TestSQLiteStorageHealthcheck:
    """Tests for health checking."""

    @pytest.mark.anyio
    async def test_healthcheck_pass(self, storage):
        """Test healthcheck on healthy storage."""
        is_healthy = await storage.healthcheck()
        assert is_healthy is True

    @pytest.mark.anyio
    async def test_healthcheck_fail_not_initialized(self):
        """Test healthcheck fails when not initialized."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        is_healthy = await storage.healthcheck()
        assert is_healthy is False

    @pytest.mark.anyio
    async def test_healthcheck_after_shutdown(self, storage):
        """Test healthcheck fails after shutdown."""
        await storage.shutdown()
        is_healthy = await storage.healthcheck()
        assert is_healthy is False


class TestSQLiteStorageConnectionString:
    """Tests for connection string property."""

    def test_connection_string_memory(self):
        """Test connection string for in-memory database."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        assert storage.connection_string == "sqlite+aiosqlite:///:memory:"

    def test_connection_string_file(self):
        """Test connection string for file-based database."""
        storage = SQLiteStorage(
            database_url="sqlite+aiosqlite:////tmp/test.db"
        )
        assert "sqlite+aiosqlite:///" in storage.connection_string
        assert "test.db" in storage.connection_string

    def test_connection_string_no_credentials(self):
        """Test that SQLite URLs contain no credentials to redact."""
        storage = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        # SQLite should never have credentials
        assert "***" not in storage.connection_string


class TestSQLiteStorageDataPersistence:
    """Tests for basic CRUD operations."""

    @pytest.mark.anyio
    async def test_insert_and_retrieve(self, storage_with_tables):
        """Test inserting and retrieving data."""
        from sqlalchemy import select
        from chatterbox.persistence.schema import User
        from uuid import uuid4

        # Insert
        user_id = str(uuid4())
        async with storage_with_tables.get_session() as session:
            user = User(id=user_id, username="alice")
            session.add(user)
            await session.flush()

        # Retrieve
        async with storage_with_tables.get_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            retrieved = result.scalars().first()
            assert retrieved is not None
            assert retrieved.username == "alice"

    @pytest.mark.anyio
    async def test_transaction_rollback_on_error(self, storage_with_tables):
        """Test that transactions are rolled back on error."""
        from sqlalchemy import select
        from chatterbox.persistence.schema import User
        from uuid import uuid4

        # Attempt to insert with duplicate username (will fail due to unique constraint)
        # First insert succeeds
        user1_id = str(uuid4())
        async with storage_with_tables.get_session() as session:
            user = User(id=user1_id, username="bob")
            session.add(user)

        # Try to insert duplicate (should rollback)
        user2_id = str(uuid4())
        try:
            async with storage_with_tables.get_session() as session:
                user2 = User(id=user2_id, username="bob")
                session.add(user2)
                await session.flush()
        except Exception:
            pass  # Expected

        # Verify only first user exists
        async with storage_with_tables.get_session() as session:
            result = await session.execute(
                select(User).where(User.username == "bob")
            )
            users = result.scalars().all()
            assert len(users) == 1
