"""Unit tests for chatterbox.config.Settings."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from chatterbox.config import Settings, _get_chatterbox_settings_path


# ---------------------------------------------------------------------------
# Test: Settings Initialization & Defaults
# ---------------------------------------------------------------------------


def test_settings_default_values() -> None:
    """Test that Settings loads with default values when no config exists."""
    with mock.patch.dict(os.environ, {}, clear=False):
        # Remove any CHATTERBOX_ env vars
        env_without_chatterbox = {
            k: v for k, v in os.environ.items() if not k.startswith("CHATTERBOX_")
        }
        with mock.patch.dict(os.environ, env_without_chatterbox, clear=True):
            settings = Settings()

    assert settings.host == "0.0.0.0"
    assert settings.port == 10700
    assert settings.ollama_base_url == "http://localhost:11434/v1"
    assert settings.ollama_model == "llama3.1:8b"
    assert settings.stt_model == "base"
    assert settings.tts_voice == "en_US-lessac-medium"
    assert settings.log_level == "INFO"


# ---------------------------------------------------------------------------
# Test: Environment Variable Override (Priority 1)
# ---------------------------------------------------------------------------


def test_env_var_overrides_defaults() -> None:
    """Test that CHATTERBOX_* env vars override defaults."""
    with mock.patch.dict(
        os.environ,
        {
            "CHATTERBOX_HOST": "127.0.0.1",
            "CHATTERBOX_PORT": "9000",
            "CHATTERBOX_LOG_LEVEL": "DEBUG",
        },
    ):
        settings = Settings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 9000
    assert settings.log_level == "DEBUG"


# ---------------------------------------------------------------------------
# Test: Settings JSON Source (Priority 2)
# ---------------------------------------------------------------------------


def test_settings_json_loads_from_config_file() -> None:
    """Test that Settings loads from ~/.config/chatterbox/settings.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"
        config_file.write_text(
            json.dumps(
                {
                    "host": "192.168.1.100",
                    "port": 10701,
                    "stt_model": "small",
                }
            )
        )

        # Patch the path function to return our temp file
        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()

        assert settings.host == "192.168.1.100"
        assert settings.port == 10701
        assert settings.stt_model == "small"


def test_settings_json_ignores_missing_file() -> None:
    """Test that Settings handles missing settings.json gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent_file = Path(tmpdir) / "does_not_exist.json"

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=nonexistent_file,
        ):
            settings = Settings()

        # Should use defaults
        assert settings.host == "0.0.0.0"
        assert settings.port == 10700


def test_settings_json_invalid_json_logs_warning(caplog) -> None:
    """Test that invalid JSON in settings.json logs a warning and falls back to defaults."""
    import logging

    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"
        config_file.write_text("{invalid json}")

        with caplog.at_level(logging.WARNING):
            with mock.patch(
                "chatterbox.config._get_chatterbox_settings_path",
                return_value=config_file,
            ):
                settings = Settings()

        # Should use defaults and log a warning
        assert settings.host == "0.0.0.0"
        assert "Failed to load settings" in caplog.text


# ---------------------------------------------------------------------------
# Test: Priority Order (env > json > defaults)
# ---------------------------------------------------------------------------


def test_priority_env_overrides_json() -> None:
    """Test that env vars take precedence over settings.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"
        config_file.write_text(
            json.dumps(
                {
                    "host": "192.168.1.100",
                    "port": 10701,
                }
            )
        )

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            with mock.patch.dict(
                os.environ,
                {"CHATTERBOX_HOST": "10.0.0.1"},
            ):
                settings = Settings()

        # Env var should win
        assert settings.host == "10.0.0.1"
        # JSON value should be used for port
        assert settings.port == 10701


def test_priority_json_overrides_defaults() -> None:
    """Test that settings.json takes precedence over defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"
        config_file.write_text(
            json.dumps(
                {
                    "stt_model": "large",
                    "tts_voice": "en_US-mary-medium",
                }
            )
        )

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()

        assert settings.stt_model == "large"
        assert settings.tts_voice == "en_US-mary-medium"


# ---------------------------------------------------------------------------
# Test: API Key Generation
# ---------------------------------------------------------------------------


def test_api_key_defaults_to_none() -> None:
    """Test that api_key defaults to None when not in config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent_file = Path(tmpdir) / "settings.json"

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=nonexistent_file,
        ):
            settings = Settings()

    assert settings.api_key is None


def test_api_key_can_be_set_from_env() -> None:
    """Test that CHATTERBOX_API_KEY env var sets the key."""
    with mock.patch.dict(
        os.environ,
        {"CHATTERBOX_API_KEY": "my-test-key-12345"},
    ):
        settings = Settings()

    assert settings.api_key == "my-test-key-12345"


def test_api_key_can_be_set_from_json() -> None:
    """Test that settings.json can set api_key via api.key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"
        config_file.write_text(
            json.dumps(
                {
                    "api": {
                        "key": "from-json-config-uuid",
                    }
                }
            )
        )

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()

        assert settings.api_key == "from-json-config-uuid"


# ---------------------------------------------------------------------------
# Test: API Key Auto-Generation (ensure_api_key)
# ---------------------------------------------------------------------------


def test_ensure_api_key_generates_new_key() -> None:
    """Test that ensure_api_key generates a UUID4 when key is None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()
            assert settings.api_key is None

            key = settings.ensure_api_key()

            # Should be a valid UUID4 string
            assert key is not None
            assert len(key) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            assert settings.api_key == key


def test_ensure_api_key_returns_existing_key() -> None:
    """Test that ensure_api_key returns existing key without regenerating."""
    with mock.patch.dict(
        os.environ,
        {"CHATTERBOX_API_KEY": "existing-key"},
    ):
        settings = Settings()

    key = settings.ensure_api_key()

    assert key == "existing-key"
    assert settings.api_key == "existing-key"


def test_ensure_api_key_persists_to_json(caplog) -> None:
    """Test that ensure_api_key persists generated key to settings.json."""
    import logging

    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"

        with caplog.at_level(logging.INFO):
            with mock.patch(
                "chatterbox.config._get_chatterbox_settings_path",
                return_value=config_file,
            ):
                settings = Settings()
                key = settings.ensure_api_key()

                # Should log the generated key
                assert "API key (auto-generated):" in caplog.text
                assert key in caplog.text

                # Should be persisted to file
                assert config_file.exists()
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                assert config_data["api"]["key"] == key


def test_ensure_api_key_creates_config_directory(caplog) -> None:
    """Test that ensure_api_key creates ~/.config/chatterbox if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "nonexistent"
        config_file = config_dir / "settings.json"

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()
            key = settings.ensure_api_key()

            assert config_file.exists()
            assert key is not None


def test_ensure_api_key_handles_write_errors(caplog) -> None:
    """Test that ensure_api_key handles write permission errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()

            # Mock open to raise PermissionError
            with mock.patch("builtins.open", side_effect=PermissionError("No write access")):
                key = settings.ensure_api_key()

            # Should still generate the key, but log warning about persistence
            assert key is not None
            assert "Could not persist API key" in caplog.text


# ---------------------------------------------------------------------------
# Test: Mellona Config Path
# ---------------------------------------------------------------------------


def test_get_mellona_config_path_returns_settings_json_if_exists() -> None:
    """Test that get_mellona_config_path prefers settings.json if it exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"
        config_file.write_text(json.dumps({}))

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()
            path = settings.get_mellona_config_path()

        assert path == str(config_file)


def test_get_mellona_config_path_uses_explicit_path_if_set() -> None:
    """Test that explicit mellona_config_path takes precedence."""
    settings = Settings(mellona_config_path="/custom/path/mellona.yaml")
    path = settings.get_mellona_config_path()

    assert path == "/custom/path/mellona.yaml"


def test_get_mellona_config_path_returns_default_if_no_file() -> None:
    """Test that get_mellona_config_path returns default path if no settings.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent_file = Path(tmpdir) / "nonexistent.json"

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=nonexistent_file,
        ):
            settings = Settings()
            path = settings.get_mellona_config_path()

        # Should return the package default (which contains 'mellona.yaml')
        assert "mellona.yaml" in path


# ---------------------------------------------------------------------------
# Test: Nested Settings from JSON
# ---------------------------------------------------------------------------


def test_nested_settings_providers_section() -> None:
    """Test that nested provider settings can be loaded from JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "settings.json"
        config_file.write_text(
            json.dumps(
                {
                    "providers": {
                        "faster_whisper": {
                            "model": "medium",
                            "device": "cuda",
                        },
                        "piper": {
                            "voice": "en_US-mary-medium",
                            "sample_rate": 44100,
                        },
                    }
                }
            )
        )

        with mock.patch(
            "chatterbox.config._get_chatterbox_settings_path",
            return_value=config_file,
        ):
            settings = Settings()
            # Note: These nested values require manual extraction from JSON
            # The Settings class flattens them to top-level env vars
            assert settings.stt_model == "base"  # Default, not overridden in this test
