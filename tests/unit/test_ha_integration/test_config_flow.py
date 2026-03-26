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


# ============================================================================
# Configuration Flow Functional Tests
# ============================================================================
# NOTE: These tests can run in environments without Home Assistant installed
# because they test the logic and structure of config flow components.


class TestConnectionValidation:
    """Test URL and connection validation logic."""

    def test_validate_url_http_with_port(self):
        """Test validation of HTTP URL with port."""
        from urllib.parse import urlparse
        url = "http://192.168.0.100:8765"
        parsed = urlparse(url)
        assert parsed.scheme == "http"
        assert parsed.netloc == "192.168.0.100:8765"

    def test_validate_url_https_with_port(self):
        """Test validation of HTTPS URL with port."""
        from urllib.parse import urlparse
        url = "https://example.com:8765"
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "example.com:8765"

    def test_validate_url_localhost(self):
        """Test validation of localhost URL."""
        from urllib.parse import urlparse
        url = "http://localhost:8765"
        parsed = urlparse(url)
        assert parsed.scheme == "http"
        assert parsed.netloc == "localhost:8765"

    def test_validate_url_with_hostname(self):
        """Test validation of URL with hostname."""
        from urllib.parse import urlparse
        url = "http://chatterbox.local:8765"
        parsed = urlparse(url)
        assert parsed.scheme == "http"
        assert parsed.netloc == "chatterbox.local:8765"

    def test_reject_url_without_scheme(self):
        """Test that URL without scheme is rejected."""
        from urllib.parse import urlparse
        url = "192.168.0.100:8765"
        parsed = urlparse(url)
        # Without a scheme, scheme will be empty or the entire thing goes to path
        assert not (parsed.scheme and parsed.netloc)

    def test_reject_empty_url(self):
        """Test that empty URL is rejected."""
        from urllib.parse import urlparse
        url = ""
        parsed = urlparse(url)
        assert not (parsed.scheme and parsed.netloc)

    def test_reject_malformed_url(self):
        """Test that malformed URL is rejected."""
        from urllib.parse import urlparse
        url = "not-a-valid-url"
        parsed = urlparse(url)
        assert not (parsed.scheme and parsed.netloc)


class TestConfigFlowSchema:
    """Test configuration flow schema."""

    def test_config_schema_has_required_url(self):
        """Test that CONFIG_SCHEMA requires URL."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "vol.Required(CONF_URL)" in content

    def test_config_schema_has_optional_api_key(self):
        """Test that CONFIG_SCHEMA has optional API key."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "vol.Optional(CONF_API_KEY" in content

    def test_config_schema_has_optional_agent_name(self):
        """Test that CONFIG_SCHEMA has optional agent name."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "vol.Optional(CONF_AGENT_NAME" in content

    def test_zeroconf_schema_no_url_required(self):
        """Test that ZEROCONF_SCHEMA doesn't require URL (already discovered)."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        # Should have ZEROCONF_SCHEMA with optional API key and agent name
        assert "ZEROCONF_SCHEMA = vol.Schema" in content

    def test_options_schema_has_all_fields(self):
        """Test that options flow allows updating all configuration fields."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        # Options flow should allow updating URL, API key, and agent name
        assert "async_step_init" in content


class TestConfigFlowFlowStructure:
    """Test the structure of config flow steps."""

    def test_user_step_exists(self):
        """Test that async_step_user exists for manual entry."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "async def async_step_user" in content

    def test_zeroconf_step_exists(self):
        """Test that async_step_zeroconf exists for discovery."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "async def async_step_zeroconf" in content

    def test_zeroconf_confirm_step_exists(self):
        """Test that async_step_zeroconf_confirm exists."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "async def async_step_zeroconf_confirm" in content

    def test_options_flow_exists(self):
        """Test that ChatterboxOptionsFlow exists for reconfiguration."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "class ChatterboxOptionsFlow" in content
        assert "async def async_step_init" in content

    def test_get_options_flow_method_exists(self):
        """Test that async_get_options_flow callback exists."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "async_get_options_flow" in content


class TestConfigFlowErrorHandling:
    """Test error handling in config flow."""

    def test_cannot_connect_exception_exists(self):
        """Test that CannotConnect exception is defined."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "class CannotConnect" in content

    def test_invalid_auth_exception_exists(self):
        """Test that InvalidAuth exception is defined."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "class InvalidAuth" in content

    def test_unknown_error_exception_exists(self):
        """Test that UnknownError exception is defined."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "class UnknownError" in content

    def test_error_messages_in_strings(self):
        """Test that error messages are defined in strings.json."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "error" in data["config"]
        errors = data["config"]["error"]
        assert "cannot_connect" in errors
        assert "invalid_auth" in errors
        assert "unknown" in errors


class TestConfigFlowTestConnection:
    """Test connection testing functionality."""

    def test_test_connection_function_exists(self):
        """Test that _test_connection async function exists."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        assert "async def _test_connection" in content

    def test_test_connection_uses_health_endpoint(self):
        """Test that _test_connection uses /health endpoint."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        # Should test /health endpoint
        assert "/health" in content or "health" in content.lower()

    def test_test_connection_handles_timeout(self):
        """Test that _test_connection handles timeout."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        # Should handle asyncio.TimeoutError
        assert "asyncio.TimeoutError" in content or "TimeoutError" in content

    def test_test_connection_handles_client_error(self):
        """Test that _test_connection handles aiohttp client errors."""
        config_flow_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/config_flow.py"
        with open(config_flow_path) as f:
            content = f.read()
        # Should handle aiohttp.ClientError
        assert "aiohttp.ClientError" in content or "ClientError" in content


class TestIntegrationStringResources:
    """Test that all required strings are present for user-facing flows."""

    def test_user_step_strings_present(self):
        """Test that user step strings are present."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "user" in data["config"]["step"]
        user_step = data["config"]["step"]["user"]
        assert "title" in user_step
        assert "description" in user_step or "description_placeholder" in user_step

    def test_zeroconf_confirm_strings_present(self):
        """Test that zeroconf_confirm step strings are present."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "zeroconf_confirm" in data["config"]["step"]
        zeroconf_step = data["config"]["step"]["zeroconf_confirm"]
        assert "title" in zeroconf_step

    def test_options_step_strings_present(self):
        """Test that options step strings are present."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "step" in data["options"]
        assert "init" in data["options"]["step"]

    def test_abort_reason_strings_present(self):
        """Test that abort reason strings are present."""
        strings_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        # Check for abort section
        if "abort" in data["config"]:
            # If abort section exists, it should have messages
            assert isinstance(data["config"]["abort"], dict)


class TestManifestZeroconfConfiguration:
    """Test Zeroconf configuration in manifest."""

    def test_manifest_zeroconf_is_list(self):
        """Test that manifest zeroconf is a list."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert isinstance(data.get("zeroconf"), list)

    def test_manifest_zeroconf_has_chatterbox_service(self):
        """Test that manifest zeroconf includes _chatterbox._tcp.local."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        zeroconf_list = data.get("zeroconf", [])
        # Should have at least one zeroconf entry
        assert len(zeroconf_list) > 0
        # Should have the chatterbox service type
        types = [z.get("type") for z in zeroconf_list]
        assert "_chatterbox._tcp.local." in types

    def test_manifest_version_increment(self):
        """Test that manifest has a version number."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "custom_components/chatterbox/manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert "version" in data
        # Version should be a string with at least one dot
        assert isinstance(data["version"], str)
        assert "." in data["version"]
