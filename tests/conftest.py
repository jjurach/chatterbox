"""
Pytest configuration for the chatterbox test suite.

This module configures pytest behavior and filters deprecation warnings.
"""

import warnings
import sys
import pytest

# Configure warnings immediately when conftest is loaded
# This needs to happen before any imports that might trigger warnings

try:
    from langchain_core._api import LangChainDeprecationWarning
except ImportError:
    # Fallback if module structure changes
    LangChainDeprecationWarning = Warning

# Suppress Wyoming's audioop deprecation warning (not our code to fix)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*'audioop' is deprecated.*",
)

# Suppress LangChain deprecated agent warnings (using langchain-classic intentionally)
warnings.filterwarnings(
    "ignore",
    category=LangChainDeprecationWarning,
    message=".*LangChain agents will continue to be supported.*",
)

# Suppress LangChain memory migration warnings
warnings.filterwarnings(
    "ignore",
    category=LangChainDeprecationWarning,
    message=".*migration guide.*",
)


def pytest_configure(config):
    """Configure pytest additional settings."""
    # Register warnings as expected and should not fail tests
    config.addinivalue_line(
        "filterwarnings",
        "ignore:.*LangChain agents will continue to be supported.*",
    )


# Async database fixtures
try:
    import pytest_asyncio
    from chatterbox.persistence.backends.sqlite import SQLiteStorage

    @pytest_asyncio.fixture
    async def storage():
        """Create an in-memory SQLite storage with tables."""
        store = SQLiteStorage(database_url="sqlite+aiosqlite:///:memory:")
        await store.initialize()
        await store.create_tables()
        yield store
        await store.shutdown()

    @pytest_asyncio.fixture
    async def async_session(storage):
        """Get an async session from storage."""
        async with storage.get_session() as session:
            yield session

except ImportError:
    pass
