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
