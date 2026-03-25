"""Serial log capture service for ESP32 device logs.

This service reads structured JSON log entries from an ESP32 device via serial
connection and manages log file storage with automatic rotation.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import serial
except ImportError:
    serial = None

from chatterbox.config.serial_logging import (
    RotationPolicy,
    SerialConnectionConfig,
    SerialLoggingSettings,
)

logger = logging.getLogger(__name__)


class LogEntry:
    """Represents a parsed log entry from device.

    Attributes:
        timestamp: Milliseconds since epoch
        level: Log level (DEBUG, INFO, WARN, ERROR)
        module: Module identifier (e.g., "audio.capture")
        message: Human-readable message
        context: Optional structured context data
        trace_id: Optional correlation ID
        error_code: Optional error code
        stack_trace: Optional stack trace
    """

    def __init__(
        self,
        timestamp: int,
        level: str,
        module: str,
        message: str,
        context: Optional[dict] = None,
        trace_id: Optional[str] = None,
        error_code: Optional[int] = None,
        stack_trace: Optional[str] = None,
    ):
        """Initialize a log entry.

        Args:
            timestamp: Milliseconds since epoch
            level: Log level (DEBUG, INFO, WARN, ERROR)
            module: Module identifier
            message: Human-readable message
            context: Optional context dictionary
            trace_id: Optional trace ID
            error_code: Optional error code
            stack_trace: Optional stack trace
        """
        self.timestamp = timestamp
        self.level = level
        self.module = module
        self.message = message
        self.context = context or {}
        self.trace_id = trace_id
        self.error_code = error_code
        self.stack_trace = stack_trace

    @classmethod
    def from_json_line(cls, json_line: str) -> Optional["LogEntry"]:
        """Parse a log entry from JSON line.

        Args:
            json_line: JSON string representing log entry

        Returns:
            LogEntry instance, or None if parsing fails
        """
        try:
            data = json.loads(json_line)

            # Validate required fields
            required = ["timestamp", "level", "module", "message"]
            if not all(field in data for field in required):
                logger.warning(
                    f"Log entry missing required fields: {json_line[:100]}"
                )
                return None

            return cls(
                timestamp=data["timestamp"],
                level=data["level"],
                module=data["module"],
                message=data["message"],
                context=data.get("context"),
                trace_id=data.get("trace_id"),
                error_code=data.get("error_code"),
                stack_trace=data.get("stack_trace"),
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse log entry: {e}")
            return None

    def to_json_dict(self) -> dict:
        """Convert log entry to JSON-serializable dictionary.

        Returns:
            Dictionary representation of log entry
        """
        result = {
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "message": self.message,
        }

        if self.context:
            result["context"] = self.context
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.error_code is not None:
            result["error_code"] = self.error_code
        if self.stack_trace:
            result["stack_trace"] = self.stack_trace

        return result

    def to_json_line(self) -> str:
        """Serialize log entry to JSON line.

        Returns:
            JSON string with single entry
        """
        return json.dumps(self.to_json_dict())


class LogFileRotator:
    """Manages log file rotation and retention.

    Handles time-based (daily) and size-based rotation, archive management,
    and cleanup of old log files based on retention policy.
    """

    def __init__(
        self,
        log_dir: Path,
        prefix: str = "chatterbox-logs",
        suffix: str = ".json",
        policy: Optional[RotationPolicy] = None,
    ):
        """Initialize log file rotator.

        Args:
            log_dir: Directory for log files
            prefix: Log filename prefix
            suffix: Log filename suffix
            policy: Rotation policy (uses defaults if not provided)
        """
        self.log_dir = log_dir
        self.prefix = prefix
        self.suffix = suffix
        self.policy = policy or RotationPolicy()

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_today_log_path(self) -> Path:
        """Get log file path for today's date.

        Returns:
            Path for today's log file
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"{self.prefix}_{today}{self.suffix}"

    def get_rotated_log_path(self, timestamp_str: Optional[str] = None) -> Path:
        """Get log file path for size-based rotation.

        Args:
            timestamp_str: Timestamp string (YYYY-MM-DD_HH-MM-SS), uses now if not provided

        Returns:
            Path for rotated log file
        """
        if timestamp_str is None:
            timestamp_str = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        return self.log_dir / f"{self.prefix}_{timestamp_str}{self.suffix}"

    def should_rotate_by_size(self, log_path: Path) -> bool:
        """Check if log file should be rotated based on size.

        Args:
            log_path: Path to current log file

        Returns:
            True if file size exceeds policy limit
        """
        if not log_path.exists():
            return False

        file_size = log_path.stat().st_size
        return file_size >= self.policy.max_file_size_bytes

    def should_rotate_by_date(self, log_path: Path) -> bool:
        """Check if log file should be rotated based on date.

        Args:
            log_path: Path to current log file

        Returns:
            True if log file is from previous day
        """
        if not self.policy.rotate_daily or not log_path.exists():
            return False

        # Check filename matches today's date
        today_path = self.get_today_log_path()
        return log_path.name != today_path.name

    def rotate(self, current_log_path: Path) -> Optional[Path]:
        """Rotate current log file if needed.

        Args:
            current_log_path: Path to current log file

        Returns:
            New log file path if rotation occurred, None otherwise
        """
        if self.should_rotate_by_date(current_log_path):
            # Date-based rotation to today's path
            new_path = self.get_today_log_path()
            logger.info(f"Rotating log (date) from {current_log_path.name} to {new_path.name}")
            return new_path

        if self.should_rotate_by_size(current_log_path):
            # Size-based rotation to timestamped path
            new_path = self.get_rotated_log_path()
            logger.info(f"Rotating log (size) from {current_log_path.name} to {new_path.name}")
            return new_path

        return None

    def cleanup_old_logs(self) -> None:
        """Delete log files older than retention period.

        Based on filename date parsing and retention policy.
        """
        if self.policy.retention_days < 1:
            return

        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.retention_days)

        for log_file in self.log_dir.glob(f"{self.prefix}_*{self.suffix}"):
            try:
                # Parse date from filename (YYYY-MM-DD_...)
                name_parts = log_file.stem.split("_")
                if len(name_parts) >= 2:
                    date_str = name_parts[1]  # YYYY-MM-DD part
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if file_date < cutoff_date:
                        logger.info(f"Deleting old log file: {log_file.name}")
                        log_file.unlink()
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse date from {log_file.name}: {e}")

    async def cleanup_old_logs_async(self) -> None:
        """Async wrapper for cleanup_old_logs."""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.cleanup_old_logs)


class SerialLogCapture:
    """Captures and stores device logs from serial connection.

    This service reads JSON-formatted log entries from an ESP32 device via serial
    connection, validates them, and writes them to log files with automatic
    rotation and retention management.

    Attributes:
        serial_config: Serial connection configuration
        rotation_policy: Log rotation policy
        is_connected: True if currently connected to device
    """

    def __init__(
        self,
        settings: Optional[SerialLoggingSettings] = None,
        serial_config: Optional[SerialConnectionConfig] = None,
        rotation_policy: Optional[RotationPolicy] = None,
    ):
        """Initialize serial log capture service.

        Args:
            settings: SerialLoggingSettings (loads from env if not provided)
            serial_config: Serial connection config (created from settings if not provided)
            rotation_policy: Log rotation policy (created from settings if not provided)

        Raises:
            ImportError: If pyserial is not installed
        """
        if serial is None:
            raise ImportError("pyserial is required for serial_log_capture. Install with: pip install pyserial")

        if settings is None:
            from chatterbox.config.serial_logging import get_serial_logging_settings

            settings = get_serial_logging_settings()

        self.settings = settings
        self.serial_config = serial_config or SerialConnectionConfig(
            port=settings.serial_port,
            baud_rate=settings.serial_baud_rate,
            timeout_seconds=settings.serial_timeout_seconds,
            buffer_size_bytes=settings.serial_buffer_size,
            max_reconnect_attempts=settings.service_reconnect_max_attempts,
            reconnect_backoff_ms=settings.service_reconnect_backoff_ms,
        )
        self.rotation_policy = rotation_policy or RotationPolicy(
            rotate_daily=settings.log_rotate_daily,
            max_file_size_bytes=settings.log_max_size_bytes,
            retention_days=settings.log_retention_days,
            archive_enabled=settings.log_archive_enabled,
            archive_compression=settings.log_archive_compression,
        )

        self.log_dir = settings.get_log_directory_path()
        self.rotator = LogFileRotator(
            log_dir=self.log_dir,
            prefix=settings.log_prefix,
            suffix=settings.log_suffix,
            policy=self.rotation_policy,
        )

        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.current_log_path: Optional[Path] = None
        self._read_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0

    async def connect(self) -> bool:
        """Connect to serial device.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.serial_port = serial.Serial(
                port=self.serial_config.port,
                baudrate=self.serial_config.baud_rate,
                timeout=self.serial_config.timeout_seconds,
            )
            self.is_connected = True
            self._reconnect_attempts = 0
            logger.info(f"Connected to {self.serial_config.port} @ {self.serial_config.baud_rate} baud")
            return True
        except (serial.SerialException, OSError) as e:
            logger.error(f"Failed to connect to {self.serial_config.port}: {e}")
            self.is_connected = False
            return False

    async def close(self) -> None:
        """Close serial connection and stop reading."""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self.serial_port:
            self.serial_port.close()
            self.is_connected = False
            logger.info("Serial connection closed")

    async def read_logs(self) -> None:
        """Read logs from serial connection in background.

        This coroutine runs indefinitely, reading log entries from the device
        and writing them to log files with rotation. Should be run as a background
        task.

        Handles reconnection on failure.
        """
        while True:
            try:
                if not self.is_connected:
                    if not await self.connect():
                        # Exponential backoff for reconnection
                        wait_ms = min(
                            self.serial_config.reconnect_backoff_ms * (2 ** self._reconnect_attempts),
                            30000,  # Max 30 seconds
                        )
                        logger.info(f"Retrying connection in {wait_ms}ms")
                        await asyncio.sleep(wait_ms / 1000)
                        self._reconnect_attempts += 1
                        if self._reconnect_attempts > self.serial_config.max_reconnect_attempts:
                            logger.error(f"Max reconnection attempts ({self.serial_config.max_reconnect_attempts}) exceeded")
                            self._reconnect_attempts = 0
                        continue

                await self._read_and_write_logs()

            except asyncio.CancelledError:
                logger.info("Log reading cancelled")
                await self.close()
                break
            except Exception as e:
                logger.error(f"Unexpected error in read_logs: {e}", exc_info=True)
                self.is_connected = False
                await asyncio.sleep(1)

    async def _read_and_write_logs(self) -> None:
        """Read from serial and write to log file.

        Internal method that performs the actual read/write loop.
        """
        buffer = ""

        while self.is_connected:
            try:
                # Non-blocking read with timeout
                if self.serial_port and self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_config.buffer_size_bytes)
                    buffer += data.decode("utf-8", errors="replace")

                    # Process complete lines
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if line:
                            await self._process_log_line(line)
                else:
                    # Yield to event loop
                    await asyncio.sleep(0.01)

            except serial.SerialException as e:
                logger.error(f"Serial read error: {e}")
                self.is_connected = False
                break

    async def _process_log_line(self, line: str) -> None:
        """Process a single log line.

        Args:
            line: Raw log line from device
        """
        entry = LogEntry.from_json_line(line)
        if entry is None:
            return

        # Rotate if needed
        if self.current_log_path is None:
            self.current_log_path = self.rotator.get_today_log_path()

        new_path = self.rotator.rotate(self.current_log_path)
        if new_path:
            self.current_log_path = new_path
            # Cleanup old logs when rotating
            await self.rotator.cleanup_old_logs_async()

        # Write log entry
        try:
            # Append to file
            with open(self.current_log_path, "a", encoding="utf-8") as f:
                f.write(entry.to_json_line() + "\n")
        except IOError as e:
            logger.error(f"Failed to write log file: {e}")

    def start_background_reading(self) -> asyncio.Task:
        """Start background log reading task.

        Returns:
            asyncio.Task that runs the read_logs coroutine
        """
        self._read_task = asyncio.create_task(self.read_logs())
        return self._read_task

    async def read_single_entry(self, timeout_seconds: float = 5.0) -> Optional[LogEntry]:
        """Read a single log entry with timeout (for testing).

        Args:
            timeout_seconds: Maximum wait time for entry

        Returns:
            LogEntry if received, None if timeout
        """
        if not self.is_connected:
            if not await self.connect():
                return None

        try:
            buffer = ""
            start_time = asyncio.get_event_loop().time()

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout_seconds:
                    logger.warning("Timeout waiting for log entry")
                    return None

                if self.serial_port and self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_config.buffer_size_bytes)
                    buffer += data.decode("utf-8", errors="replace")

                    if "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        entry = LogEntry.from_json_line(line.strip())
                        if entry:
                            return entry
                else:
                    await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"Error reading single entry: {e}")
            return None

    def get_stats(self) -> dict:
        """Get service statistics.

        Returns:
            Dictionary with current stats
        """
        return {
            "is_connected": self.is_connected,
            "serial_port": self.serial_config.port,
            "baud_rate": self.serial_config.baud_rate,
            "log_directory": str(self.log_dir),
            "current_log_file": str(self.current_log_path) if self.current_log_path else None,
            "reconnect_attempts": self._reconnect_attempts,
        }


__all__ = [
    "SerialLogCapture",
    "LogEntry",
    "LogFileRotator",
]
