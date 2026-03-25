"""Unit tests for serial log capture service."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatterbox.config.serial_logging import (
    RotationPolicy,
    SerialConnectionConfig,
    SerialLoggingSettings,
)
from chatterbox.services.serial_log_capture import (
    LogEntry,
    LogFileRotator,
    SerialLogCapture,
)


# ---------------------------------------------------------------------------
# LogEntry Tests
# ---------------------------------------------------------------------------


class TestLogEntry:
    """Test LogEntry parsing and serialization."""

    def test_create_basic_log_entry(self) -> None:
        """Test creating a basic log entry."""
        entry = LogEntry(
            timestamp=1714521600000,
            level="INFO",
            module="startup",
            message="Device initialized",
        )

        assert entry.timestamp == 1714521600000
        assert entry.level == "INFO"
        assert entry.module == "startup"
        assert entry.message == "Device initialized"
        assert entry.context == {}
        assert entry.trace_id is None

    def test_create_log_entry_with_context(self) -> None:
        """Test creating log entry with context."""
        context = {"sample_rate": 16000, "channels": 1}
        entry = LogEntry(
            timestamp=1714521605234,
            level="INFO",
            module="audio.capture",
            message="Audio buffer full",
            context=context,
        )

        assert entry.context == context

    def test_create_log_entry_with_error(self) -> None:
        """Test creating log entry with error code."""
        entry = LogEntry(
            timestamp=1714521610500,
            level="ERROR",
            module="wifi.connection",
            message="Connection failed",
            error_code=3,
            stack_trace="WiFiError: Max retries exceeded",
        )

        assert entry.level == "ERROR"
        assert entry.error_code == 3
        assert entry.stack_trace is not None

    def test_parse_basic_json_line(self) -> None:
        """Test parsing basic JSON log line."""
        json_line = '{"timestamp": 1714521600000, "level": "INFO", "module": "startup", "message": "Device initialized"}'
        entry = LogEntry.from_json_line(json_line)

        assert entry is not None
        assert entry.timestamp == 1714521600000
        assert entry.level == "INFO"
        assert entry.module == "startup"
        assert entry.message == "Device initialized"

    def test_parse_json_with_context(self) -> None:
        """Test parsing JSON with context."""
        json_line = '{"timestamp": 1714521605234, "level": "INFO", "module": "audio.capture", "message": "Capturing", "context": {"sample_rate": 16000}}'
        entry = LogEntry.from_json_line(json_line)

        assert entry is not None
        assert entry.context == {"sample_rate": 16000}

    def test_parse_json_with_all_fields(self) -> None:
        """Test parsing JSON with all optional fields."""
        json_line = '{"timestamp": 1714521610500, "level": "ERROR", "module": "wifi", "message": "Failed", "error_code": 3, "trace_id": "abc123", "stack_trace": "error here", "context": {"attempts": 5}}'
        entry = LogEntry.from_json_line(json_line)

        assert entry is not None
        assert entry.error_code == 3
        assert entry.trace_id == "abc123"
        assert entry.stack_trace == "error here"
        assert entry.context == {"attempts": 5}

    def test_parse_invalid_json_returns_none(self) -> None:
        """Test parsing invalid JSON returns None."""
        entry = LogEntry.from_json_line("{invalid json}")
        assert entry is None

    def test_parse_missing_required_field_returns_none(self) -> None:
        """Test parsing JSON missing required field returns None."""
        json_line = '{"timestamp": 1714521600000, "level": "INFO"}'  # missing module and message
        entry = LogEntry.from_json_line(json_line)
        assert entry is None

    def test_serialize_to_json_dict(self) -> None:
        """Test serializing entry to JSON dict."""
        entry = LogEntry(
            timestamp=1714521600000,
            level="INFO",
            module="startup",
            message="Test",
        )

        result = entry.to_json_dict()
        assert result["timestamp"] == 1714521600000
        assert result["level"] == "INFO"
        assert result["module"] == "startup"
        assert result["message"] == "Test"

    def test_serialize_to_json_line(self) -> None:
        """Test serializing entry to JSON line."""
        entry = LogEntry(
            timestamp=1714521600000,
            level="INFO",
            module="startup",
            message="Test",
        )

        json_line = entry.to_json_line()
        parsed = json.loads(json_line)
        assert parsed["timestamp"] == 1714521600000
        assert parsed["level"] == "INFO"

    def test_round_trip_serialization(self) -> None:
        """Test round-trip: parse -> serialize -> parse."""
        original = '{"timestamp": 1714521600000, "level": "INFO", "module": "startup", "message": "Test", "context": {"key": "value"}}'
        entry = LogEntry.from_json_line(original)
        assert entry is not None

        serialized = entry.to_json_line()
        reparsed = LogEntry.from_json_line(serialized)
        assert reparsed is not None
        assert reparsed.timestamp == entry.timestamp
        assert reparsed.level == entry.level
        assert reparsed.module == entry.module
        assert reparsed.message == entry.message
        assert reparsed.context == entry.context


# ---------------------------------------------------------------------------
# LogFileRotator Tests
# ---------------------------------------------------------------------------


class TestLogFileRotator:
    """Test log file rotation logic."""

    def test_create_rotator(self, tmp_path: Path) -> None:
        """Test creating a log file rotator."""
        rotator = LogFileRotator(log_dir=tmp_path)
        assert rotator.log_dir == tmp_path
        assert tmp_path.exists()

    def test_get_today_log_path(self, tmp_path: Path) -> None:
        """Test getting today's log file path."""
        rotator = LogFileRotator(log_dir=tmp_path)
        path = rotator.get_today_log_path()

        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert today in str(path)
        assert str(path).endswith(".json")

    def test_get_rotated_log_path(self, tmp_path: Path) -> None:
        """Test getting rotated log file path."""
        rotator = LogFileRotator(log_dir=tmp_path)
        path = rotator.get_rotated_log_path("2026-03-25_14-30-45")

        assert "2026-03-25_14-30-45" in str(path)
        assert str(path).endswith(".json")

    def test_should_rotate_by_size(self, tmp_path: Path) -> None:
        """Test size-based rotation check."""
        rotator = LogFileRotator(
            log_dir=tmp_path,
            policy=RotationPolicy(max_file_size_bytes=100),
        )

        log_file = tmp_path / "test.json"
        log_file.write_text("x" * 50)

        # Below threshold
        assert not rotator.should_rotate_by_size(log_file)

        # Exceed threshold
        log_file.write_text("x" * 101)
        assert rotator.should_rotate_by_size(log_file)

    def test_should_rotate_by_date(self, tmp_path: Path) -> None:
        """Test date-based rotation check."""
        rotator = LogFileRotator(log_dir=tmp_path)

        # Create file with yesterday's date
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        old_file = tmp_path / f"chatterbox-logs_{yesterday}.json"
        old_file.write_text("test")

        assert rotator.should_rotate_by_date(old_file)

        # File with today's date should not rotate
        today_file = rotator.get_today_log_path()
        today_file.write_text("test")
        assert not rotator.should_rotate_by_date(today_file)

    def test_rotate_by_date(self, tmp_path: Path) -> None:
        """Test rotating log file by date."""
        rotator = LogFileRotator(log_dir=tmp_path)

        # Create old file
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        old_file = tmp_path / f"chatterbox-logs_{yesterday}.json"
        old_file.write_text("old content")

        new_path = rotator.rotate(old_file)
        assert new_path is not None
        assert new_path.name != old_file.name

    def test_rotate_by_size(self, tmp_path: Path) -> None:
        """Test rotating log file by size."""
        rotator = LogFileRotator(
            log_dir=tmp_path,
            policy=RotationPolicy(max_file_size_bytes=50),
        )

        log_file = tmp_path / "chatterbox-logs_2026-03-25.json"
        log_file.write_text("x" * 100)

        new_path = rotator.rotate(log_file)
        assert new_path is not None
        assert new_path.name != log_file.name

    def test_cleanup_old_logs(self, tmp_path: Path) -> None:
        """Test cleanup of old log files."""
        rotator = LogFileRotator(
            log_dir=tmp_path,
            policy=RotationPolicy(retention_days=7),
        )

        # Create files at different dates
        old_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_file = tmp_path / f"chatterbox-logs_{old_date}.json"
        old_file.write_text("old")

        recent_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        recent_file = tmp_path / f"chatterbox-logs_{recent_date}.json"
        recent_file.write_text("recent")

        rotator.cleanup_old_logs()

        assert not old_file.exists(), "Old file should be deleted"
        assert recent_file.exists(), "Recent file should be kept"

    @pytest.mark.anyio
    async def test_cleanup_old_logs_async(self, tmp_path: Path) -> None:
        """Test async cleanup of old logs."""
        rotator = LogFileRotator(
            log_dir=tmp_path,
            policy=RotationPolicy(retention_days=7),
        )

        old_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_file = tmp_path / f"chatterbox-logs_{old_date}.json"
        old_file.write_text("old")

        await rotator.cleanup_old_logs_async()
        assert not old_file.exists()


# ---------------------------------------------------------------------------
# SerialLogCapture Tests
# ---------------------------------------------------------------------------


class TestSerialLogCapture:
    """Test serial log capture service."""

    def test_create_with_settings(self, tmp_path: Path) -> None:
        """Test creating service with custom settings."""
        settings = SerialLoggingSettings(
            serial_port="/dev/ttyUSB0",
            serial_baud_rate=115200,
            log_directory=str(tmp_path),
        )

        with patch("chatterbox.services.serial_log_capture.serial"):
            service = SerialLogCapture(settings=settings)

            assert service.settings == settings
            assert service.is_connected is False
            assert service.serial_port is None

    def test_create_without_pyserial_raises_error(self, tmp_path: Path) -> None:
        """Test that ImportError is raised if pyserial not available."""
        settings = SerialLoggingSettings(log_directory=str(tmp_path))

        with patch("chatterbox.services.serial_log_capture.serial", None):
            with pytest.raises(ImportError, match="pyserial"):
                SerialLogCapture(settings=settings)

    @pytest.mark.anyio
    async def test_connect_success(self, tmp_path: Path) -> None:
        """Test successful connection to serial port."""
        mock_serial = MagicMock()
        mock_serial_class = MagicMock(return_value=mock_serial)

        with patch("chatterbox.services.serial_log_capture.serial.Serial", mock_serial_class):
            settings = SerialLoggingSettings(
                serial_port="/dev/ttyUSB0",
                log_directory=str(tmp_path),
            )
            service = SerialLogCapture(settings=settings)

            result = await service.connect()

            assert result is True
            assert service.is_connected is True
            mock_serial_class.assert_called_once()

    @pytest.mark.anyio
    async def test_connect_failure(self, tmp_path: Path) -> None:
        """Test failed connection to serial port."""
        import serial as serial_module

        with patch("chatterbox.services.serial_log_capture.serial.Serial") as mock_serial:
            mock_serial.side_effect = serial_module.SerialException("Port not found")

            settings = SerialLoggingSettings(
                serial_port="/dev/ttyUSB999",
                log_directory=str(tmp_path),
            )
            service = SerialLogCapture(settings=settings)

            result = await service.connect()

            assert result is False
            assert service.is_connected is False

    @pytest.mark.anyio
    async def test_close_connection(self, tmp_path: Path) -> None:
        """Test closing connection."""
        mock_serial = MagicMock()

        with patch("chatterbox.services.serial_log_capture.serial.Serial", return_value=mock_serial):
            settings = SerialLoggingSettings(log_directory=str(tmp_path))
            service = SerialLogCapture(settings=settings)

            await service.connect()
            assert service.is_connected is True

            await service.close()

            assert service.is_connected is False
            mock_serial.close.assert_called_once()

    @pytest.mark.anyio
    async def test_process_log_line(self, tmp_path: Path) -> None:
        """Test processing a single log line."""
        mock_serial = MagicMock()

        with patch("chatterbox.services.serial_log_capture.serial.Serial", return_value=mock_serial):
            settings = SerialLoggingSettings(log_directory=str(tmp_path))
            service = SerialLogCapture(settings=settings)

            await service.connect()

            json_line = '{"timestamp": 1714521600000, "level": "INFO", "module": "startup", "message": "Test"}'
            await service._process_log_line(json_line)

            # Check that log file was created and written
            log_file = tmp_path / f"chatterbox-logs_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
            assert log_file.exists()

    @pytest.mark.anyio
    async def test_process_multiple_log_lines(self, tmp_path: Path) -> None:
        """Test processing multiple log lines."""
        mock_serial = MagicMock()

        with patch("chatterbox.services.serial_log_capture.serial.Serial", return_value=mock_serial):
            settings = SerialLoggingSettings(log_directory=str(tmp_path))
            service = SerialLogCapture(settings=settings)

            await service.connect()

            lines = [
                '{"timestamp": 1714521600000, "level": "INFO", "module": "startup", "message": "Started"}',
                '{"timestamp": 1714521600100, "level": "INFO", "module": "audio", "message": "Ready"}',
                '{"timestamp": 1714521600200, "level": "ERROR", "module": "wifi", "message": "Failed"}',
            ]

            for line in lines:
                await service._process_log_line(line)

            log_file = tmp_path / f"chatterbox-logs_{datetime.utcnow().strftime('%Y-%m-%d')}.json"
            content = log_file.read_text()
            lines_in_file = content.strip().split("\n")
            assert len(lines_in_file) == 3

    @pytest.mark.anyio
    async def test_rotation_on_date_change(self, tmp_path: Path) -> None:
        """Test log rotation when date changes."""
        mock_serial = MagicMock()

        with patch("chatterbox.services.serial_log_capture.serial.Serial", return_value=mock_serial):
            settings = SerialLoggingSettings(log_directory=str(tmp_path))
            service = SerialLogCapture(settings=settings)

            await service.connect()

            # Create old log file with yesterday's date
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            old_file = tmp_path / f"chatterbox-logs_{yesterday}.json"
            old_file.write_text("old content\n")

            service.current_log_path = old_file

            # Process new entry
            json_line = '{"timestamp": 1714521600000, "level": "INFO", "module": "startup", "message": "Test"}'
            await service._process_log_line(json_line)

            # Log path should have rotated to today
            today = datetime.utcnow().strftime("%Y-%m-%d")
            today_file = tmp_path / f"chatterbox-logs_{today}.json"
            assert service.current_log_path == today_file

    def test_get_stats(self, tmp_path: Path) -> None:
        """Test getting service statistics."""
        with patch("chatterbox.services.serial_log_capture.serial"):
            settings = SerialLoggingSettings(
                serial_port="/dev/ttyUSB0",
                log_directory=str(tmp_path),
            )
            service = SerialLogCapture(settings=settings)

            stats = service.get_stats()

            assert stats["serial_port"] == "/dev/ttyUSB0"
            assert stats["baud_rate"] == 115200
            assert stats["is_connected"] is False
            assert stats["log_directory"] == str(tmp_path)

    @pytest.mark.anyio
    async def test_start_background_reading(self, tmp_path: Path) -> None:
        """Test starting background reading task."""
        with patch("chatterbox.services.serial_log_capture.serial"):
            settings = SerialLoggingSettings(log_directory=str(tmp_path))
            service = SerialLogCapture(settings=settings)

            # Mock the connection and read loop
            with patch.object(service, "connect", new_callable=AsyncMock, return_value=False):
                task = service.start_background_reading()

                # Let task run briefly
                await asyncio.sleep(0.1)

                # Cancel task
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.anyio
    async def test_read_single_entry_timeout(self, tmp_path: Path) -> None:
        """Test read_single_entry timeout."""
        mock_serial = MagicMock()
        mock_serial.in_waiting = 0  # No data available

        with patch("chatterbox.services.serial_log_capture.serial.Serial", return_value=mock_serial):
            settings = SerialLoggingSettings(log_directory=str(tmp_path))
            service = SerialLogCapture(settings=settings)

            await service.connect()

            result = await service.read_single_entry(timeout_seconds=0.1)
            assert result is None


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestSerialLogCaptureIntegration:
    """Integration tests for serial log capture."""

    @pytest.mark.anyio
    async def test_full_log_capture_and_rotation_cycle(self, tmp_path: Path) -> None:
        """Test complete cycle: connect, capture, rotate, cleanup."""
        mock_serial = MagicMock()

        with patch("chatterbox.services.serial_log_capture.serial.Serial", return_value=mock_serial):
            settings = SerialLoggingSettings(
                log_directory=str(tmp_path),
                log_rotate_daily=True,
                log_max_size_bytes=1000,
                log_retention_days=7,
            )
            service = SerialLogCapture(settings=settings)

            # Connect
            connected = await service.connect()
            assert connected

            # Write multiple log entries
            for i in range(5):
                json_line = json.dumps({
                    "timestamp": 1714521600000 + i * 1000,
                    "level": "INFO",
                    "module": f"module_{i}",
                    "message": f"Message {i}",
                })
                await service._process_log_line(json_line)

            # Verify logs were written
            today = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = tmp_path / f"chatterbox-logs_{today}.json"
            assert log_file.exists()

            content = log_file.read_text()
            assert content.count("\n") == 5

            # Close
            await service.close()
            assert not service.is_connected


# ---------------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------------


class TestSerialLoggingConfiguration:
    """Test configuration classes."""

    def test_rotation_policy_validation(self) -> None:
        """Test RotationPolicy validation."""
        policy = RotationPolicy(
            rotate_daily=True,
            max_file_size_bytes=10 * 1024 * 1024,
            retention_days=30,
        )
        assert policy.max_file_size_bytes > 0
        assert policy.retention_days > 0

    def test_rotation_policy_invalid_size(self) -> None:
        """Test RotationPolicy with invalid size."""
        with pytest.raises(ValueError):
            RotationPolicy(max_file_size_bytes=-1)

    def test_serial_connection_config(self) -> None:
        """Test SerialConnectionConfig."""
        config = SerialConnectionConfig(
            port="/dev/ttyUSB0",
            baud_rate=115200,
            timeout_seconds=1.0,
        )
        assert config.port == "/dev/ttyUSB0"
        assert config.baud_rate == 115200

    def test_serial_connection_config_invalid_baud(self) -> None:
        """Test SerialConnectionConfig with invalid baud rate."""
        with pytest.raises(ValueError):
            SerialConnectionConfig(baud_rate=-1)
