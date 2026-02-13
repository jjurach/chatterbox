"""Configuration for Approach A batch processing Whisper integration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioFormatConfig:
    """Audio format specifications for PCM buffering.

    This configuration defines the expected audio format for Wyoming protocol
    and ensures compatibility with Whisper transcription.
    """

    sample_rate: int = 16000  # Hz - Standard for STT
    channels: int = 1  # Mono - Single channel
    sample_width: int = 2  # Bytes - 16-bit samples
    byte_order: str = "little"  # Little-endian (S16_LE)

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if self.channels <= 0:
            raise ValueError("Channels must be positive")
        if self.sample_width <= 0:
            raise ValueError("Sample width must be positive")
        if self.byte_order not in ("little", "big"):
            raise ValueError("Byte order must be 'little' or 'big'")

    @property
    def bytes_per_second(self) -> int:
        """Calculate bytes per second of audio."""
        return self.sample_rate * self.sample_width * self.channels

    @property
    def bytes_per_millisecond(self) -> float:
        """Calculate bytes per millisecond of audio."""
        return self.bytes_per_second / 1000.0


@dataclass
class BufferConstraintsConfig:
    """Buffer size and constraint specifications.

    Defines maximum buffer sizes and safety limits for audio buffering.
    """

    max_buffer_seconds: int = 30  # Whisper maximum
    warn_threshold_percentage: float = 80.0  # Warn when buffer is 80% full
    error_threshold_percentage: float = 95.0  # Error when buffer is 95% full

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.max_buffer_seconds <= 0:
            raise ValueError("Max buffer seconds must be positive")
        if not (0 <= self.warn_threshold_percentage <= 100):
            raise ValueError("Warn threshold must be 0-100%")
        if not (0 <= self.error_threshold_percentage <= 100):
            raise ValueError("Error threshold must be 0-100%")
        if self.warn_threshold_percentage > self.error_threshold_percentage:
            raise ValueError("Warn threshold must be <= error threshold")

    def get_max_bytes(self, audio_config: AudioFormatConfig) -> int:
        """Calculate maximum buffer size in bytes.

        Args:
            audio_config: Audio format configuration

        Returns:
            Maximum buffer size in bytes
        """
        return (
            audio_config.sample_rate
            * audio_config.sample_width
            * audio_config.channels
            * self.max_buffer_seconds
        )

    def get_warn_threshold_bytes(self, audio_config: AudioFormatConfig) -> int:
        """Calculate warning threshold in bytes.

        Args:
            audio_config: Audio format configuration

        Returns:
            Bytes at which to log warning
        """
        max_bytes = self.get_max_bytes(audio_config)
        return int(max_bytes * (self.warn_threshold_percentage / 100.0))

    def get_error_threshold_bytes(self, audio_config: AudioFormatConfig) -> int:
        """Calculate error threshold in bytes.

        Args:
            audio_config: Audio format configuration

        Returns:
            Bytes at which to raise error
        """
        max_bytes = self.get_max_bytes(audio_config)
        return int(max_bytes * (self.error_threshold_percentage / 100.0))


@dataclass
class ChunkValidationConfig:
    """Chunk size validation specifications.

    Wyoming protocol typically sends 2048-3200 byte chunks.
    This configuration allows validation of chunk sizes.
    """

    expected_min_bytes: int = 2048  # Minimum expected chunk size
    expected_max_bytes: int = 3200  # Maximum typical chunk size
    allow_variable_sizes: bool = True  # Allow first/last chunks to differ
    warn_on_unexpected: bool = True  # Warn when chunks don't match expected size

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.expected_min_bytes <= 0:
            raise ValueError("Min bytes must be positive")
        if self.expected_max_bytes <= 0:
            raise ValueError("Max bytes must be positive")
        if self.expected_min_bytes > self.expected_max_bytes:
            raise ValueError("Min bytes must be <= max bytes")

    def is_expected_size(self, chunk_size: int) -> bool:
        """Check if chunk size is within expected range.

        Args:
            chunk_size: Size of chunk in bytes

        Returns:
            True if chunk size is expected
        """
        return self.expected_min_bytes <= chunk_size <= self.expected_max_bytes


@dataclass
class WhisperConfig:
    """Whisper STT service configuration."""

    model_size: str = "base"  # tiny, base, small, medium, large
    device: str = "cpu"  # cpu, cuda
    language: Optional[str] = None  # None = auto-detect
    compute_type: str = "int8"  # int8, int16, float32, float16
    timeout_seconds: int = 30  # Max time for transcription

    def __post_init__(self):
        """Validate configuration parameters."""
        valid_models = ("tiny", "base", "small", "medium", "large")
        if self.model_size not in valid_models:
            raise ValueError(f"Model size must be one of {valid_models}")

        valid_devices = ("cpu", "cuda")
        if self.device not in valid_devices:
            raise ValueError(f"Device must be one of {valid_devices}")

        valid_compute = ("int8", "int16", "float32", "float16")
        if self.compute_type not in valid_compute:
            raise ValueError(f"Compute type must be one of {valid_compute}")

        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class ErrorHandlingConfig:
    """Error handling and retry configuration."""

    max_retries: int = 3  # Maximum transcription retry attempts
    retry_backoff_ms: int = 100  # Backoff between retries in milliseconds
    clear_buffer_on_error: bool = True  # Clear buffer after critical errors
    timeout_handling: str = "error"  # "error", "return_empty", "retry"

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        if self.retry_backoff_ms < 0:
            raise ValueError("Retry backoff must be non-negative")
        if self.timeout_handling not in ("error", "return_empty", "retry"):
            raise ValueError("Timeout handling must be 'error', 'return_empty', or 'retry'")


@dataclass
class LoggingConfig:
    """Logging and observability configuration."""

    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_metrics_every_n_chunks: int = 10  # Log progress every N chunks
    detailed_chunk_logging: bool = False  # Log every chunk (verbose)
    collect_metrics: bool = True  # Enable MetricsCollector
    structured_logging: bool = False  # JSON-formatted logs

    def __post_init__(self):
        """Validate configuration parameters."""
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.log_level not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        if self.log_metrics_every_n_chunks <= 0:
            raise ValueError("Log metrics frequency must be positive")


class BatchProcessingConfig:
    """Complete configuration for Approach A batch processing.

    This master configuration combines all sub-configurations for the
    batch processing Whisper integration approach.
    """

    def __init__(
        self,
        audio_format: Optional[AudioFormatConfig] = None,
        buffer_constraints: Optional[BufferConstraintsConfig] = None,
        chunk_validation: Optional[ChunkValidationConfig] = None,
        whisper: Optional[WhisperConfig] = None,
        error_handling: Optional[ErrorHandlingConfig] = None,
        logging: Optional[LoggingConfig] = None,
    ):
        """Initialize BatchProcessingConfig with defaults.

        Args:
            audio_format: Audio format config (defaults to 16kHz mono PCM)
            buffer_constraints: Buffer constraints (defaults to 30s max)
            chunk_validation: Chunk validation rules
            whisper: Whisper service config
            error_handling: Error handling strategy
            logging: Logging configuration
        """
        self.audio_format = audio_format or AudioFormatConfig()
        self.buffer_constraints = buffer_constraints or BufferConstraintsConfig()
        self.chunk_validation = chunk_validation or ChunkValidationConfig()
        self.whisper = whisper or WhisperConfig()
        self.error_handling = error_handling or ErrorHandlingConfig()
        self.logging = logging or LoggingConfig()

    @classmethod
    def from_dict(cls, config_dict: dict) -> "BatchProcessingConfig":
        """Create configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            BatchProcessingConfig instance

        Example:
            config = BatchProcessingConfig.from_dict({
                "audio_format": {"sample_rate": 16000},
                "whisper": {"model_size": "base"},
            })
        """
        audio_format = (
            AudioFormatConfig(**config_dict.get("audio_format", {}))
            if config_dict.get("audio_format")
            else AudioFormatConfig()
        )
        buffer_constraints = (
            BufferConstraintsConfig(**config_dict.get("buffer_constraints", {}))
            if config_dict.get("buffer_constraints")
            else BufferConstraintsConfig()
        )
        chunk_validation = (
            ChunkValidationConfig(**config_dict.get("chunk_validation", {}))
            if config_dict.get("chunk_validation")
            else ChunkValidationConfig()
        )
        whisper = (
            WhisperConfig(**config_dict.get("whisper", {}))
            if config_dict.get("whisper")
            else WhisperConfig()
        )
        error_handling = (
            ErrorHandlingConfig(**config_dict.get("error_handling", {}))
            if config_dict.get("error_handling")
            else ErrorHandlingConfig()
        )
        logging = (
            LoggingConfig(**config_dict.get("logging", {}))
            if config_dict.get("logging")
            else LoggingConfig()
        )

        return cls(
            audio_format=audio_format,
            buffer_constraints=buffer_constraints,
            chunk_validation=chunk_validation,
            whisper=whisper,
            error_handling=error_handling,
            logging=logging,
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "audio_format": {
                "sample_rate": self.audio_format.sample_rate,
                "channels": self.audio_format.channels,
                "sample_width": self.audio_format.sample_width,
                "byte_order": self.audio_format.byte_order,
            },
            "buffer_constraints": {
                "max_buffer_seconds": self.buffer_constraints.max_buffer_seconds,
                "warn_threshold_percentage": (
                    self.buffer_constraints.warn_threshold_percentage
                ),
                "error_threshold_percentage": (
                    self.buffer_constraints.error_threshold_percentage
                ),
            },
            "chunk_validation": {
                "expected_min_bytes": self.chunk_validation.expected_min_bytes,
                "expected_max_bytes": self.chunk_validation.expected_max_bytes,
                "allow_variable_sizes": self.chunk_validation.allow_variable_sizes,
                "warn_on_unexpected": self.chunk_validation.warn_on_unexpected,
            },
            "whisper": {
                "model_size": self.whisper.model_size,
                "device": self.whisper.device,
                "language": self.whisper.language,
                "compute_type": self.whisper.compute_type,
                "timeout_seconds": self.whisper.timeout_seconds,
            },
            "error_handling": {
                "max_retries": self.error_handling.max_retries,
                "retry_backoff_ms": self.error_handling.retry_backoff_ms,
                "clear_buffer_on_error": self.error_handling.clear_buffer_on_error,
                "timeout_handling": self.error_handling.timeout_handling,
            },
            "logging": {
                "log_level": self.logging.log_level,
                "log_metrics_every_n_chunks": self.logging.log_metrics_every_n_chunks,
                "detailed_chunk_logging": self.logging.detailed_chunk_logging,
                "collect_metrics": self.logging.collect_metrics,
                "structured_logging": self.logging.structured_logging,
            },
        }

    def get_summary(self) -> str:
        """Get human-readable configuration summary.

        Returns:
            Formatted configuration summary string
        """
        return (
            f"BatchProcessingConfig:\n"
            f"  Audio: {self.audio_format.sample_rate}Hz, "
            f"{self.audio_format.channels}ch, "
            f"{self.audio_format.sample_width}B/sample\n"
            f"  Buffer: {self.buffer_constraints.max_buffer_seconds}s max\n"
            f"  Whisper: {self.whisper.model_size} model on {self.whisper.device}\n"
            f"  Error Handling: {self.error_handling.max_retries} max retries\n"
            f"  Logging: {self.logging.log_level} level"
        )

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"BatchProcessingConfig({self.whisper.model_size} on {self.whisper.device})"
