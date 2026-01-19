"""Metrics collection for audio processing observability."""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics for audio buffering and transcription.

    Tracks session-level, chunk-level, and transcription-level metrics
    to enable monitoring, debugging, and performance optimization.

    Attributes:
        session_id: Unique identifier for this session
        session_start_time: When the session began
        chunks_received: Number of audio chunks processed
        total_audio_bytes: Total audio data received in bytes
        transcription_start_time: When Whisper processing began
        transcription_end_time: When Whisper processing completed
        transcript_length: Length of generated transcript
    """

    def __init__(self, session_id: Optional[str] = None):
        """Initialize MetricsCollector.

        Args:
            session_id: Optional unique session identifier for logging
        """
        self.session_id = session_id or "unknown"
        self.session_start_time = time.time()

        # Chunk metrics
        self.chunks_received = 0
        self.total_audio_bytes = 0
        self.min_chunk_bytes = float("inf")
        self.max_chunk_bytes = 0

        # Transcription metrics
        self.transcription_start_time: Optional[float] = None
        self.transcription_end_time: Optional[float] = None
        self.transcript_text = ""
        self.transcript_language = "unknown"
        self.transcript_confidence = 0.0

        # Error tracking
        self.errors_encountered = 0
        self.last_error_message = ""

        logger.debug(f"MetricsCollector created for session {self.session_id}")

    def record_chunk(self, chunk_size: int) -> None:
        """Record receipt of an audio chunk.

        Args:
            chunk_size: Size of chunk in bytes
        """
        self.chunks_received += 1
        self.total_audio_bytes += chunk_size
        self.min_chunk_bytes = min(self.min_chunk_bytes, chunk_size)
        self.max_chunk_bytes = max(self.max_chunk_bytes, chunk_size)

        # Log every 10 chunks to track progress without spam
        if self.chunks_received % 10 == 0:
            logger.debug(
                f"[{self.session_id}] Chunk {self.chunks_received}: "
                f"{chunk_size} bytes, total: {self.total_audio_bytes} bytes"
            )

    def start_transcription(self) -> None:
        """Mark the start of Whisper transcription."""
        self.transcription_start_time = time.time()
        logger.debug(f"[{self.session_id}] Transcription started")

    def record_transcription_result(
        self,
        text: str,
        language: str = "unknown",
        confidence: float = 0.0,
    ) -> None:
        """Record transcription results.

        Args:
            text: Transcribed text
            language: Detected language code (e.g., 'en')
            confidence: Confidence score (0.0-1.0)
        """
        self.transcription_end_time = time.time()
        self.transcript_text = text
        self.transcript_language = language
        self.transcript_confidence = confidence

        if self.transcription_start_time is None:
            processing_time_ms = 0
        else:
            processing_time_ms = (
                self.transcription_end_time - self.transcription_start_time
            ) * 1000

        logger.info(
            f"[{self.session_id}] Transcription complete: "
            f"{processing_time_ms:.0f}ms processing, "
            f"{len(text)} chars, "
            f"confidence: {confidence:.2f}, "
            f"language: {language}"
        )

    def record_error(self, error_message: str) -> None:
        """Record that an error occurred.

        Args:
            error_message: Description of the error
        """
        self.errors_encountered += 1
        self.last_error_message = error_message

        logger.error(
            f"[{self.session_id}] Error #{self.errors_encountered}: {error_message}"
        )

    def get_elapsed_time_ms(self) -> float:
        """Get elapsed time since session start in milliseconds.

        Returns:
            Milliseconds elapsed
        """
        return (time.time() - self.session_start_time) * 1000

    def get_transcription_time_ms(self) -> float:
        """Get time spent in Whisper transcription in milliseconds.

        Returns:
            Milliseconds spent transcribing (0 if not completed)
        """
        if (
            self.transcription_start_time is None
            or self.transcription_end_time is None
        ):
            return 0.0

        return (
            self.transcription_end_time - self.transcription_start_time
        ) * 1000

    def get_average_chunk_size(self) -> float:
        """Calculate average chunk size.

        Returns:
            Average chunk size in bytes (0 if no chunks)
        """
        if self.chunks_received == 0:
            return 0.0
        return self.total_audio_bytes / self.chunks_received

    def get_audio_duration_ms(self) -> float:
        """Estimate audio duration based on data and standard format.

        Assumes 16000 Hz, 16-bit (2 bytes), mono format.

        Returns:
            Estimated audio duration in milliseconds
        """
        sample_rate = 16000
        sample_width = 2
        channels = 1

        bytes_per_sample = sample_width * channels
        if bytes_per_sample == 0:
            return 0.0

        num_samples = self.total_audio_bytes // bytes_per_sample
        duration_ms = (num_samples / sample_rate) * 1000
        return duration_ms

    def get_summary(self) -> dict:
        """Get comprehensive metrics summary.

        Returns:
            Dictionary with all collected metrics
        """
        return {
            "session_id": self.session_id,
            "elapsed_time_ms": self.get_elapsed_time_ms(),
            "chunks": {
                "received": self.chunks_received,
                "total_bytes": self.total_audio_bytes,
                "average_size": self.get_average_chunk_size(),
                "min_size": (
                    self.min_chunk_bytes
                    if self.min_chunk_bytes != float("inf")
                    else 0
                ),
                "max_size": self.max_chunk_bytes,
            },
            "audio": {
                "estimated_duration_ms": self.get_audio_duration_ms(),
            },
            "transcription": {
                "processing_time_ms": self.get_transcription_time_ms(),
                "text_length": len(self.transcript_text),
                "language": self.transcript_language,
                "confidence": self.transcript_confidence,
            },
            "errors": {
                "count": self.errors_encountered,
                "last_message": self.last_error_message,
            },
        }

    def log_summary(self) -> None:
        """Log a summary of all collected metrics."""
        summary = self.get_summary()

        logger.info(
            f"[{self.session_id}] Session summary: "
            f"{summary['chunks']['received']} chunks, "
            f"{summary['audio']['estimated_duration_ms']:.0f}ms audio, "
            f"{summary['transcription']['processing_time_ms']:.0f}ms transcription, "
            f"{summary['transcription']['text_length']} chars, "
            f"confidence: {summary['transcription']['confidence']:.2f}"
        )

        if self.errors_encountered > 0:
            logger.warning(
                f"[{self.session_id}] Session had {self.errors_encountered} error(s): "
                f"{self.last_error_message}"
            )

    def __repr__(self) -> str:
        """String representation of metrics state."""
        return (
            f"MetricsCollector({self.session_id}, "
            f"{self.chunks_received} chunks, "
            f"{self.total_audio_bytes} bytes, "
            f"{self.get_transcription_time_ms():.0f}ms transcription)"
        )
