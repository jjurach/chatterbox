"""Configuration for serial logging capture service.

This module defines settings for the serial log capture service that reads
device logs from ESP32 via serial connection and manages log rotation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class SerialLoggingSettings(BaseSettings):
    """Settings for serial logging capture service.

    Loads configuration from environment variables prefixed with CHATTERBOX_SERIAL_
    or from a .env file.
    """

    # Serial connection settings
    serial_port: str = "/dev/ttyUSB0"
    serial_baud_rate: int = 115200
    serial_timeout_seconds: float = 1.0
    serial_buffer_size: int = 4096

    # Log file settings
    log_directory: str = "/var/log/chatterbox"
    log_prefix: str = "chatterbox-logs"
    log_suffix: str = ".json"

    # Rotation settings
    log_rotate_daily: bool = True
    log_max_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_retention_days: int = 30
    log_archive_enabled: bool = False
    log_archive_compression: bool = False

    # Service settings
    service_reconnect_max_attempts: int = 5
    service_reconnect_backoff_ms: int = 5000
    service_log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="CHATTERBOX_SERIAL_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    def get_log_directory_path(self) -> Path:
        """Get log directory as Path object, creating if needed.

        Returns:
            pathlib.Path instance for log directory

        Raises:
            PermissionError: If directory cannot be created
        """
        log_dir = Path(self.log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def get_archive_directory_path(self) -> Path:
        """Get archive directory as Path object, creating if needed.

        Returns:
            pathlib.Path instance for archive directory
        """
        if not self.log_archive_enabled:
            return None
        archive_dir = Path(self.log_directory) / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir

    def validate_serial_port(self) -> bool:
        """Validate that serial port exists and is readable.

        Returns:
            True if serial port is accessible, False otherwise
        """
        port_path = Path(self.serial_port)
        return port_path.exists()

    def get_summary(self) -> str:
        """Get human-readable configuration summary.

        Returns:
            Formatted configuration summary string
        """
        return (
            f"SerialLoggingSettings:\n"
            f"  Port: {self.serial_port} @ {self.serial_baud_rate} baud\n"
            f"  Log Dir: {self.log_directory}\n"
            f"  Rotation: {'daily' if self.log_rotate_daily else 'size-based'} "
            f"(max {self.log_max_size_bytes} bytes)\n"
            f"  Retention: {self.log_retention_days} days\n"
            f"  Archive: {'enabled' if self.log_archive_enabled else 'disabled'}"
        )


@dataclass
class RotationPolicy:
    """Policy for log file rotation.

    Defines when and how log files should be rotated based on
    time and/or file size.
    """

    rotate_daily: bool = True
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    retention_days: int = 30
    archive_enabled: bool = False
    archive_compression: bool = False

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.max_file_size_bytes <= 0:
            raise ValueError("Max file size must be positive")
        if self.retention_days <= 0:
            raise ValueError("Retention days must be positive")
        if self.retention_days < 1:
            raise ValueError("Retention days must be at least 1")


@dataclass
class SerialConnectionConfig:
    """Configuration for serial connection to device.

    Defines serial port connection parameters for reading device logs.
    """

    port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200
    timeout_seconds: float = 1.0
    buffer_size_bytes: int = 4096
    max_reconnect_attempts: int = 5
    reconnect_backoff_ms: int = 5000

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.baud_rate <= 0:
            raise ValueError("Baud rate must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        if self.buffer_size_bytes <= 0:
            raise ValueError("Buffer size must be positive")
        if self.max_reconnect_attempts < 0:
            raise ValueError("Max reconnect attempts must be non-negative")
        if self.reconnect_backoff_ms <= 0:
            raise ValueError("Reconnect backoff must be positive")


def get_serial_logging_settings() -> SerialLoggingSettings:
    """Get the serial logging settings instance.

    Returns:
        SerialLoggingSettings instance with environment-loaded config
    """
    return SerialLoggingSettings()


__all__ = [
    "SerialLoggingSettings",
    "RotationPolicy",
    "SerialConnectionConfig",
    "get_serial_logging_settings",
]
