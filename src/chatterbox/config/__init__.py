"""Configuration modules for Chatterbox components."""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import JsonConfigSettingsSource

logger = logging.getLogger(__name__)


def _get_chatterbox_settings_path() -> Path:
    """Get the path to the user's chatterbox settings.json file.

    Returns:
        Path object for ~/.config/chatterbox/settings.json
    """
    config_dir = Path.home() / ".config" / "chatterbox"
    return config_dir / "settings.json"


def _flatten_nested_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested JSON config to match Settings field names.

    Converts settings like:
        {"api": {"key": "my-key"}} -> {"api_key": "my-key"}

    Args:
        data: Raw settings dictionary from JSON

    Returns:
        Flattened dictionary with field names matching Settings model
    """
    flattened = data.copy()

    # Extract api.key -> api_key
    if "api" in data and isinstance(data["api"], dict):
        if "key" in data["api"]:
            flattened["api_key"] = data["api"]["key"]

    # Extract memory.conversation_window_size -> conversation_window_size
    if "memory" in data and isinstance(data["memory"], dict):
        if "conversation_window_size" in data["memory"]:
            flattened["conversation_window_size"] = data["memory"]["conversation_window_size"]

    # Extract logging.level -> log_level
    if "logging" in data and isinstance(data["logging"], dict):
        if "level" in data["logging"]:
            flattened["log_level"] = data["logging"]["level"]

    return flattened


def _settings_json_source(settings_obj: BaseSettings) -> dict[str, Any]:
    """Load settings from ~/.config/chatterbox/settings.json if it exists.

    This is a custom settings source for pydantic-settings that loads from
    the user's config directory. Environment variables take precedence.

    Args:
        settings_obj: The Settings instance (used by pydantic-settings)

    Returns:
        Dictionary of settings loaded from JSON file, empty dict if file not found
    """
    settings_path = _get_chatterbox_settings_path()

    if not settings_path.exists():
        return {}

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return _flatten_nested_settings(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load settings from {settings_path}: {e}")
        return {}


class ChatterboxJsonSettingsSource(JsonConfigSettingsSource):
    """Custom JSON settings source that reads from ~/.config/chatterbox/settings.json."""

    def _read_files(self, files: list[str] | str | None, deep_merge: bool = False) -> dict[str, Any]:
        """Override to read from ~/.config/chatterbox/settings.json instead of default file."""
        settings_path = _get_chatterbox_settings_path()
        if settings_path.exists():
            try:
                data = super()._read_files([str(settings_path)], deep_merge=deep_merge)
                # Flatten nested structures like api.key -> api_key
                return _flatten_nested_settings(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to load settings from {settings_path}: {e}")
                return {}
        return {}


class Settings(BaseSettings):
    """Application settings loaded from environment variables and settings.json."""

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

    # API authentication
    api_key: str | None = None  # Auto-generated UUID4 if not set

    # Mellona configuration
    mellona_config_path: str | None = None  # Path to mellona config file
    mellona_profile: str = "default"  # Which mellona LLM profile to use

    model_config = SettingsConfigDict(
        env_prefix="CHATTERBOX_",
        env_file=".env",
        env_file_encoding="utf-8",
        json_file=str(_get_chatterbox_settings_path()),
        json_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from JSON (server, api, conversation, providers, etc)
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Any,
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Customize settings source priority.

        Priority order (highest to lowest):
        1. Initialization settings
        2. Environment variables (CHATTERBOX_*)
        3. ~/.config/chatterbox/settings.json
        4. .env file
        5. File secrets (.env)
        6. Default values (class defaults)
        """
        json_settings = ChatterboxJsonSettingsSource(settings_cls)
        return (
            init_settings,
            env_settings,
            json_settings,
            dotenv_settings,
            file_secret_settings,
        )

    def ensure_api_key(self) -> str:
        """Ensure an API key exists, generating and persisting it if necessary.

        If api_key is None, generates a new UUID4 and attempts to persist it
        to ~/.config/chatterbox/settings.json.

        Returns:
            The API key (either existing or newly generated)
        """
        if self.api_key:
            return self.api_key

        # Generate new key
        self.api_key = str(uuid.uuid4())
        logger.info(f"API key (auto-generated): {self.api_key}")

        # Try to persist to settings.json
        settings_path = _get_chatterbox_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new one
        if settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not read existing settings: {e}, starting fresh")
                config = {}
        else:
            config = {}

        # Ensure api section exists and set key
        if "api" not in config:
            config["api"] = {}
        config["api"]["key"] = self.api_key

        # Write back
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            logger.debug(f"Persisted API key to {settings_path}")
        except OSError as e:
            logger.warning(f"Could not persist API key to {settings_path}: {e}")

        return self.api_key

    @classmethod
    def _get_default_mellona_config_path(cls) -> str:
        """Get the default path to the mellona config file.

        Returns the path to mellona.yaml in the chatterbox package directory.
        This is deprecated; prefer ~/.config/chatterbox/settings.json instead.
        """
        package_dir = Path(__file__).parent.parent
        return str(package_dir / "mellona.yaml")

    def get_mellona_config_path(self) -> str:
        """Get the mellona config path, using settings.json path if available.

        Returns:
            Path to the mellona config file (prefer settings.json)
        """
        if self.mellona_config_path:
            return self.mellona_config_path

        # Prefer settings.json location if it exists
        settings_path = _get_chatterbox_settings_path()
        if settings_path.exists():
            return str(settings_path)

        # Fall back to package default (deprecated)
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
