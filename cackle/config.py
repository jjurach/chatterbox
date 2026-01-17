"""
Configuration management for the Chatterbox3B Wyoming Voice Assistant.

This module provides a Settings class that loads configuration from environment
variables, allowing easy configuration without code changes.
"""

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

    # TTS settings
    tts_voice: str = "en_US-lessac-medium"
    tts_sample_rate: int = 22050

    # Service mode
    server_mode: str = "full"  # full, stt_only, tts_only, combined

    # REST API settings
    rest_port: int = 8080
    enable_rest: bool = False

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="CHATTERBOX_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


def get_settings() -> Settings:
    """Get the application settings instance."""
    return Settings()
