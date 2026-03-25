"""Tests for Chatterbox config flow.

Note: These tests are designed to work in environments where HomeAssistant
is not installed. They verify the structure and syntax of the config flow
module. Full functional testing requires a Home Assistant environment.
"""

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest


class TestConfigFlowStructure:
    """Test the structure and syntax of the config flow module."""

    def test_config_flow_file_exists(self):
        """Test that config_flow.py exists."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        assert config_flow_path.exists(), "config_flow.py does not exist"

    def test_config_flow_syntax(self):
        """Test that config_flow.py has valid Python syntax."""
        import py_compile
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        try:
            py_compile.compile(str(config_flow_path), doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"config_flow.py has syntax errors: {e}")

    def test_init_file_exists(self):
        """Test that __init__.py exists."""
        init_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/__init__.py"
        assert init_path.exists(), "__init__.py does not exist"

    def test_const_file_exists(self):
        """Test that const.py exists."""
        const_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/const.py"
        assert const_path.exists(), "const.py does not exist"

    def test_manifest_file_exists(self):
        """Test that manifest.json exists."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/manifest.json"
        assert manifest_path.exists(), "manifest.json does not exist"

    def test_strings_file_exists(self):
        """Test that strings.json exists."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        assert strings_path.exists(), "strings.json does not exist"


class TestStringResources:
    """Test the string resources for config flow."""

    def test_strings_json_is_valid(self):
        """Test that strings.json is valid JSON."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert data is not None

    def test_strings_json_has_config_section(self):
        """Test that strings.json has config section."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "config" in data, "strings.json missing 'config' section"
        assert "step" in data["config"], "strings.json config missing 'step' section"

    def test_strings_json_has_user_step(self):
        """Test that strings.json has user step."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "user" in data["config"]["step"], "strings.json missing user step"
        user_step = data["config"]["step"]["user"]
        assert "title" in user_step, "user step missing title"
        assert "data" in user_step, "user step missing data"

    def test_strings_json_has_zeroconf_confirm_step(self):
        """Test that strings.json has zeroconf_confirm step."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "zeroconf_confirm" in data["config"]["step"], "strings.json missing zeroconf_confirm step"

    def test_strings_json_has_error_messages(self):
        """Test that strings.json has error messages."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "error" in data["config"], "strings.json config missing 'error' section"
        errors = data["config"]["error"]
        assert "cannot_connect" in errors, "missing cannot_connect error"
        assert "invalid_auth" in errors, "missing invalid_auth error"
        assert "unknown" in errors, "missing unknown error"

    def test_strings_json_has_options_section(self):
        """Test that strings.json has options section."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "options" in data, "strings.json missing 'options' section"
        assert "step" in data["options"], "strings.json options missing 'step' section"

    def test_translations_en_json_is_valid(self):
        """Test that translations/en.json is valid JSON."""
        en_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/translations/en.json"
        assert en_path.exists(), "translations/en.json does not exist"
        with open(en_path) as f:
            data = json.load(f)
        assert data is not None

    def test_translations_en_mirrors_strings(self):
        """Test that translations/en.json mirrors strings.json structure."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        en_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/translations/en.json"

        with open(strings_path) as f:
            strings_data = json.load(f)
        with open(en_path) as f:
            en_data = json.load(f)

        # Both should have the same top-level sections
        assert set(strings_data.keys()) == set(en_data.keys()), "strings.json and en.json have different keys"


class TestManifest:
    """Test the manifest.json file."""

    def test_manifest_is_valid_json(self):
        """Test that manifest.json is valid JSON."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert data is not None

    def test_manifest_has_required_fields(self):
        """Test that manifest.json has required fields."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert "domain" in data, "manifest.json missing 'domain'"
        assert data["domain"] == "chatterbox", "domain should be 'chatterbox'"
        assert "name" in data, "manifest.json missing 'name'"
        assert "version" in data, "manifest.json missing 'version'"
        assert "config_flow" in data, "manifest.json missing 'config_flow'"
        assert data["config_flow"] is True, "config_flow should be True"

    def test_manifest_has_zeroconf_config(self):
        """Test that manifest.json has zeroconf configuration."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert "zeroconf" in data, "manifest.json missing 'zeroconf'"
        assert isinstance(data["zeroconf"], list), "zeroconf should be a list"
        assert len(data["zeroconf"]) > 0, "zeroconf list should not be empty"
        assert any(z.get("type") == "_chatterbox._tcp.local." for z in data["zeroconf"]), \
            "zeroconf should include _chatterbox._tcp.local."


class TestConstFile:
    """Test the const.py file."""

    def test_const_has_constants(self):
        """Test that const.py defines required constants."""
        const_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/const.py"
        with open(const_path) as f:
            content = f.read()

        # Check that required constants are defined
        assert "DOMAIN" in content, "const.py missing DOMAIN"
        assert "CONF_URL" in content, "const.py missing CONF_URL"
        assert "CONF_API_KEY" in content, "const.py missing CONF_API_KEY"
        assert "CONF_AGENT_NAME" in content, "const.py missing CONF_AGENT_NAME"
        assert "DEFAULT_AGENT_NAME" in content, "const.py missing DEFAULT_AGENT_NAME"


class TestConfigFlowLogic:
    """Test the logic of URL validation (without importing HA)."""

    def test_valid_url_parsing(self):
        """Test that valid URLs parse correctly."""
        urls = [
            "http://192.168.0.100:8765",
            "http://localhost:8765",
            "http://chatterbox.local:8765",
            "https://example.com:8765",
        ]

        for url in urls:
            parsed = urlparse(url)
            assert parsed.scheme, f"URL {url} has no scheme"
            assert parsed.netloc, f"URL {url} has no netloc"

    def test_invalid_url_parsing(self):
        """Test that invalid URLs fail validation."""
        urls = [
            "",
            "not-a-url",
            "192.168.0.100:8765",  # Missing scheme
            "://example.com",  # Missing scheme name
        ]

        for url in urls:
            parsed = urlparse(url)
            # Missing scheme or netloc
            assert not (parsed.scheme and parsed.netloc), \
                f"URL {url} should fail validation but passed"


class TestConfigFlowImports:
    """Test that the config_flow module has proper imports."""

    def test_config_flow_imports(self):
        """Test that config_flow.py has required imports."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()

        # Check for required imports/classes
        assert "import aiohttp" in content or "from aiohttp" in content, "config_flow missing aiohttp import"
        assert "import voluptuous" in content or "from voluptuous" in content, "config_flow missing voluptuous import"
        assert "import asyncio" in content or "from asyncio" in content, "config_flow missing asyncio import"

        # Check for class definitions
        assert "class ChatterboxConfigFlow" in content, "config_flow missing ChatterboxConfigFlow class"
        assert "class ChatterboxOptionsFlow" in content, "config_flow missing ChatterboxOptionsFlow class"
        assert "class CannotConnect" in content, "config_flow missing CannotConnect exception"

        # Check for key methods
        assert "async def _test_connection" in content, "config_flow missing _test_connection method"
        assert "async def async_step_user" in content, "config_flow missing async_step_user method"
        assert "async def async_step_zeroconf" in content, "config_flow missing async_step_zeroconf method"
        assert "async def async_step_zeroconf_confirm" in content, "config_flow missing async_step_zeroconf_confirm method"


class TestFileReadability:
    """Test that all files are readable and have reasonable sizes."""

    def test_config_flow_file_size(self):
        """Test that config_flow.py has reasonable size."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        size = config_flow_path.stat().st_size
        assert size > 1000, "config_flow.py seems too small"
        assert size < 100000, "config_flow.py seems too large"

    def test_strings_json_file_size(self):
        """Test that strings.json has reasonable size."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        size = strings_path.stat().st_size
        assert size > 100, "strings.json seems too small"
        assert size < 50000, "strings.json seems too large"
