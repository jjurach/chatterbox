"""Configuration modules for Chatterbox components."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 10700

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b"
    ollama_temperature: float = 0.7

    # Memory settings
    conversation_window_size: int = 3

    # STT settings
    stt_model: str = "base"  # tiny, base, small, medium, large
    stt_device: str = "cpu"  # cpu, cuda
    stt_language: str | None = None  # None = auto-detect
    whisper_cache_dir: str | None = None  # None = ~/.cache/chatterbox/whisper

    # TTS settings
    tts_voice: str = "en_US-lessac-medium"
    tts_sample_rate: int = 22050
    piper_cache_dir: str | None = None  # None = ~/.cache/chatterbox/piper

    # Service mode
    server_mode: str = "full"  # full, stt_only, tts_only, combined

    # REST API settings
    rest_port: int = 8080
    enable_rest: bool = False

    # Logging
    log_level: str = "INFO"

    # Mellona configuration
    mellona_config_path: str | None = None  # Path to mellona config file
    mellona_profile: str = "default"  # Which mellona LLM profile to use

    model_config = SettingsConfigDict(
        env_prefix="CHATTERBOX_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @classmethod
    def _get_default_mellona_config_path(cls) -> str:
        """Get the default path to the mellona config file.

        Returns the path to mellona.yaml in the chatterbox package directory.
        """
        package_dir = Path(__file__).parent.parent
        return str(package_dir / "mellona.yaml")

    def get_mellona_config_path(self) -> str:
        """Get the mellona config path, using default if not set.

        Returns:
            Path to the mellona config file.
        """
        if self.mellona_config_path:
            return self.mellona_config_path
        return self._get_default_mellona_config_path()


def get_settings() -> Settings:
    """Get the application settings instance."""
    return Settings()


# Import batch processing configs
from chatterbox.config.batch_processing import (
    AudioFormatConfig,
    BatchProcessingConfig,
    BufferConstraintsConfig,
    ChunkValidationConfig,
    ErrorHandlingConfig,
    LoggingConfig,
    WhisperConfig,
)
from chatterbox.config.serial_logging import (
    RotationPolicy,
    SerialConnectionConfig,
    SerialLoggingSettings,
    get_serial_logging_settings,
)

__all__ = [
    "Settings",
    "get_settings",
    "AudioFormatConfig",
    "BufferConstraintsConfig",
    "ChunkValidationConfig",
    "WhisperConfig",
    "ErrorHandlingConfig",
    "LoggingConfig",
    "BatchProcessingConfig",
    "SerialLoggingSettings",
    "RotationPolicy",
    "SerialConnectionConfig",
    "get_serial_logging_settings",
]
