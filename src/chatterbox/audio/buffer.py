"""Audio buffering utilities for streaming PCM audio."""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class AudioBuffer:
    """Manages PCM audio buffering for STT processing.

    This class handles accumulation of PCM audio chunks and provides utilities
    for buffer management, validation, and metrics.

    Attributes:
        buffer: The underlying bytearray for audio storage
        sample_rate: Sample rate in Hz (default: 16000)
        channels: Number of audio channels (default: 1 - mono)
        sample_width: Bytes per sample (default: 2 - 16-bit)
        max_seconds: Maximum buffer duration in seconds (default: 30 - Whisper limit)
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
        max_seconds: int = 30,
    ):
        """Initialize AudioBuffer.

        Args:
            sample_rate: Sample rate in Hz. Default: 16000 Hz
            channels: Number of audio channels. Default: 1 (mono)
            sample_width: Bytes per sample. Default: 2 (16-bit)
            max_seconds: Maximum buffer size in seconds. Default: 30 (Whisper limit)

        Raises:
            ValueError: If parameters are invalid
        """
        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if channels <= 0:
            raise ValueError("Channels must be positive")
        if sample_width <= 0:
            raise ValueError("Sample width must be positive")
        if max_seconds <= 0:
            raise ValueError("Max seconds must be positive")

        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.max_seconds = max_seconds

        # Calculate maximum buffer size in bytes
        self.max_bytes = sample_rate * sample_width * channels * max_seconds

        # Initialize buffer
        self.buffer = bytearray()
        self.chunks_added = 0

        logger.debug(
            f"AudioBuffer initialized: {sample_rate}Hz, {channels}ch, "
            f"{sample_width} bytes/sample, max {max_seconds}s ({self.max_bytes} bytes)"
        )

    def add_chunk(self, chunk: bytes) -> None:
        """Add an audio chunk to the buffer.

        Args:
            chunk: Audio data chunk (bytes)

        Raises:
            ValueError: If chunk is empty
            RuntimeError: If adding chunk would exceed buffer limit
        """
        if not chunk:
            raise ValueError("Cannot add empty chunk")

        new_size = len(self.buffer) + len(chunk)

        if new_size > self.max_bytes:
            logger.warning(
                f"Buffer size limit approaching: "
                f"{len(self.buffer)} + {len(chunk)} = {new_size} > {self.max_bytes}"
            )
            raise RuntimeError(
                f"Adding {len(chunk)} bytes would exceed buffer limit of {self.max_bytes}"
            )

        self.buffer.extend(chunk)
        self.chunks_added += 1

        # Log every 10 chunks to avoid log spam
        if self.chunks_added % 10 == 0:
            logger.debug(
                f"Added {self.chunks_added} chunks, "
                f"buffer size: {len(self.buffer)} bytes, "
                f"duration: {self.get_duration_ms():.1f}ms"
            )

    def get_duration_ms(self) -> float:
        """Calculate current audio duration in milliseconds.

        Returns:
            Duration of buffered audio in milliseconds
        """
        bytes_per_sample = self.sample_width * self.channels
        if bytes_per_sample == 0:
            return 0.0

        num_samples = len(self.buffer) // bytes_per_sample
        duration_ms = (num_samples / self.sample_rate) * 1000
        return duration_ms

    def get_size_bytes(self) -> int:
        """Get current buffer size in bytes.

        Returns:
            Number of bytes in buffer
        """
        return len(self.buffer)

    def get_size_percentage(self) -> float:
        """Get buffer utilization as percentage of maximum.

        Returns:
            Percentage of maximum buffer used (0-100)
        """
        if self.max_bytes == 0:
            return 0.0
        return (len(self.buffer) / self.max_bytes) * 100.0

    def get_expected_samples(self) -> int:
        """Get number of complete samples in buffer.

        Returns:
            Number of complete audio samples
        """
        bytes_per_sample = self.sample_width * self.channels
        if bytes_per_sample == 0:
            return 0
        return len(self.buffer) // bytes_per_sample

    def is_empty(self) -> bool:
        """Check if buffer is empty.

        Returns:
            True if buffer has no audio data
        """
        return len(self.buffer) == 0

    def is_full(self) -> bool:
        """Check if buffer is at maximum capacity.

        Returns:
            True if buffer is at or near maximum
        """
        return len(self.buffer) >= self.max_bytes

    def get_and_clear(self) -> bytes:
        """Get buffer contents and clear the buffer.

        Returns:
            Bytes of audio data that were in buffer
        """
        result = bytes(self.buffer)
        self.buffer.clear()
        self.chunks_added = 0

        logger.debug(
            f"Buffer cleared: returned {len(result)} bytes, "
            f"duration: {(len(result) / self.sample_rate / self.sample_width / self.channels * 1000):.1f}ms"
        )

        return result

    def clear(self) -> None:
        """Clear the buffer without returning contents.

        This is useful when discarding audio due to error conditions.
        """
        size_before = len(self.buffer)
        self.buffer.clear()
        self.chunks_added = 0

        if size_before > 0:
            logger.debug(f"Buffer cleared: discarded {size_before} bytes")

    def validate_format(
        self,
        expected_sample_rate: int = 16000,
        expected_channels: int = 1,
        expected_sample_width: int = 2,
    ) -> bool:
        """Validate that buffer audio format matches expected format.

        Args:
            expected_sample_rate: Expected sample rate in Hz
            expected_channels: Expected number of channels
            expected_sample_width: Expected bytes per sample

        Returns:
            True if format matches expectations
        """
        matches = (
            self.sample_rate == expected_sample_rate
            and self.channels == expected_channels
            and self.sample_width == expected_sample_width
        )

        if not matches:
            logger.error(
                f"Audio format mismatch: "
                f"expected {expected_sample_rate}Hz {expected_channels}ch {expected_sample_width}B/sample, "
                f"got {self.sample_rate}Hz {self.channels}ch {self.sample_width}B/sample"
            )

        return matches

    def get_statistics(self) -> dict:
        """Get buffer statistics for monitoring and debugging.

        Returns:
            Dictionary with buffer statistics
        """
        duration_ms = self.get_duration_ms()
        size_bytes = self.get_size_bytes()
        size_pct = self.get_size_percentage()
        num_samples = self.get_expected_samples()

        return {
            "size_bytes": size_bytes,
            "size_percentage": size_pct,
            "duration_ms": duration_ms,
            "num_chunks": self.chunks_added,
            "num_samples": num_samples,
            "is_empty": self.is_empty(),
            "is_full": self.is_full(),
            "format": {
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "sample_width": self.sample_width,
            },
            "limits": {
                "max_bytes": self.max_bytes,
                "max_seconds": self.max_seconds,
            },
        }

    def __len__(self) -> int:
        """Get buffer size in bytes."""
        return len(self.buffer)

    def __bool__(self) -> bool:
        """True if buffer has data."""
        return not self.is_empty()

    def __repr__(self) -> str:
        """String representation of buffer state."""
        return (
            f"AudioBuffer({self.sample_rate}Hz, {self.channels}ch, "
            f"{len(self.buffer)}/{self.max_bytes} bytes, "
            f"{self.get_duration_ms():.1f}ms)"
        )
