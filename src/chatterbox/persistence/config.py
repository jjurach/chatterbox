"""
Configuration for persistence layer.

Reads database configuration from environment variables and provides
settings for storage backend initialization.

Supported environment variables:
- CHATTERBOX_DATABASE_URL: Full connection string (overrides DATABASE_BACKEND and others)
- CHATTERBOX_DATABASE_BACKEND: "sqlite" or "postgresql" (default: "sqlite")
- CHATTERBOX_DATABASE_PATH: Path to SQLite file (default: "./chatterbox.db")
- CHATTERBOX_DATABASE_ECHO: "true" or "false" to log SQL (default: "false")
- CHATTERBOX_DATABASE_POOL_SIZE: Connection pool size (default: 10, ignored for SQLite)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class PersistenceConfig:
    """Configuration for the persistence layer.

    Attributes:
        database_backend: "sqlite" or "postgresql".
        database_url: Full connection string (overrides other DB settings).
        database_path: Path to SQLite file (only for SQLite backend).
        database_echo: If True, log all SQL statements.
        pool_size: Connection pool size (for PostgreSQL).
        pool_recycle: Recycle connections after N seconds (for PostgreSQL).
    """

    database_backend: Literal["sqlite", "postgresql"] = "sqlite"
    database_url: str | None = None
    database_path: str = "./chatterbox.db"
    database_echo: bool = False
    pool_size: int = 10
    pool_recycle: int = 3600

    @classmethod
    def from_env(cls) -> PersistenceConfig:
        """Load configuration from environment variables.

        Priority order:
        1. CHATTERBOX_DATABASE_URL (if set, overrides everything)
        2. Individual settings (CHATTERBOX_DATABASE_BACKEND, etc.)

        Returns:
            A PersistenceConfig instance.
        """
        # Check for explicit database URL first
        database_url = os.getenv("CHATTERBOX_DATABASE_URL")
        if database_url:
            logger.info("Using explicit DATABASE_URL from environment")
            return cls(database_url=database_url)

        # Otherwise, build from individual settings
        backend = os.getenv("CHATTERBOX_DATABASE_BACKEND", "sqlite").lower()
        if backend not in ("sqlite", "postgresql"):
            logger.warning(
                "Invalid CHATTERBOX_DATABASE_BACKEND=%r, using sqlite", backend
            )
            backend = "sqlite"

        database_path = os.getenv(
            "CHATTERBOX_DATABASE_PATH", "./chatterbox.db"
        )
        echo = os.getenv("CHATTERBOX_DATABASE_ECHO", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        pool_size = int(os.getenv("CHATTERBOX_DATABASE_POOL_SIZE", "10"))
        pool_recycle = int(os.getenv("CHATTERBOX_DATABASE_POOL_RECYCLE", "3600"))

        return cls(
            database_backend=backend,
            database_path=database_path,
            database_echo=echo,
            pool_size=pool_size,
            pool_recycle=pool_recycle,
        )

    def get_connection_url(self) -> str:
        """Build the full connection URL based on backend and settings.

        Returns:
            A connection URL suitable for SQLAlchemy.

        Raises:
            ValueError: If the backend is invalid or missing required settings.
        """
        # If an explicit URL is set, use it
        if self.database_url:
            return self.database_url

        if self.database_backend == "sqlite":
            # Normalize the database path
            if self.database_path == ":memory:":
                return "sqlite+aiosqlite:///:memory:"

            # Convert relative paths to absolute
            db_path = Path(self.database_path).resolve()
            return f"sqlite+aiosqlite:///{db_path}"

        elif self.database_backend == "postgresql":
            # PostgreSQL connection string (stub for future implementation)
            # In a real implementation, would read from environment variables
            raise NotImplementedError("PostgreSQL backend not yet implemented")

        else:
            raise ValueError(
                f"Unknown database backend: {self.database_backend}"
            )

    def __str__(self) -> str:
        """Return a string representation (with redacted credentials)."""
        url = self.get_connection_url()
        if "postgresql" in url:
            # Redact password in PostgreSQL URLs
            parts = url.split("://")
            if "@" in parts[1]:
                proto, rest = parts
                user_pass, host = rest.split("@", 1)
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    return f"{proto}://{user}:***@{host}"
        return url


# Convenience function for getting the singleton config
_config: PersistenceConfig | None = None


def get_config() -> PersistenceConfig:
    """Get or create the global persistence config.

    Returns:
        The PersistenceConfig instance.
    """
    global _config
    if _config is None:
        _config = PersistenceConfig.from_env()
        logger.info("Loaded persistence config: backend=%s", _config.database_backend)
    return _config


def reset_config() -> None:
    """Reset the global config (mainly for testing)."""
    global _config
    _config = None
