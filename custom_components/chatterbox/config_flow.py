"""Config flow for the Chatterbox integration."""

import asyncio
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from zeroconf import ZeroconfServiceInfo

from .const import CONF_AGENT_NAME, CONF_API_KEY, CONF_URL, DEFAULT_AGENT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Optional(CONF_API_KEY, default=""): str,
        vol.Optional(CONF_AGENT_NAME, default=DEFAULT_AGENT_NAME): str,
    }
)

ZEROCONF_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_API_KEY, default=""): str,
        vol.Optional(CONF_AGENT_NAME, default=DEFAULT_AGENT_NAME): str,
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""


class UnknownError(HomeAssistantError):
    """Error to indicate an unknown error."""


async def _test_connection(url: str, api_key: str) -> bool:
    """Test connection to the Chatterbox server.

    Args:
        url: The server URL
        api_key: The API key (not used for /health, but kept for consistency)

    Returns:
        True if connection successful, False otherwise

    Raises:
        CannotConnect: If the server is unreachable
    """
    try:
        # Validate URL format
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise CannotConnect("Invalid URL format")

        # Test connection to /health endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{url}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return True
                raise CannotConnect(f"Server returned status {resp.status}")
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
        _LOGGER.debug("Connection test failed: %s", err)
        raise CannotConnect(f"Failed to connect: {err}") from err


class ChatterboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chatterbox."""

    VERSION = 1
    discovered_url: Optional[str] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step (manual entry)."""
        errors = {}

        if user_input is not None:
            try:
                # Validate and test the connection
                await _test_connection(user_input[CONF_URL], user_input[CONF_API_KEY])

                # Check for duplicate config entries
                await self.async_set_unique_id(user_input[CONF_URL])
                self._abort_if_unique_id_configured()

                # Create config entry
                return self.async_create_entry(
                    title=user_input[CONF_AGENT_NAME],
                    data={
                        CONF_URL: user_input[CONF_URL],
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_AGENT_NAME: user_input[CONF_AGENT_NAME],
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during config flow: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle Zeroconf discovery."""
        # Extract hostname and port from discovery info
        # discovery_info.name is like "Chatterbox.hostname._chatterbox._tcp.local."
        # discovery_info.addresses contains IP addresses
        # discovery_info.port contains the port

        if discovery_info.addresses and discovery_info.port:
            # Use the first IP address
            ip_address = discovery_info.addresses[0]
            url = f"http://{ip_address}:{discovery_info.port}"

            # Try to set unique ID based on the discovered URL
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()

            # Store the discovered URL for the next step
            self.discovered_url = url

            return await self.async_step_zeroconf_confirm()
        else:
            _LOGGER.warning(
                "Zeroconf discovery info incomplete: %s", discovery_info
            )
            # Fall back to manual entry
            return await self.async_step_user()

    async def async_step_zeroconf_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Confirm the Zeroconf discovery and get API key + agent name."""
        errors = {}

        if user_input is not None:
            try:
                # Test connection with discovered URL
                await _test_connection(
                    self.discovered_url, user_input[CONF_API_KEY]
                )

                # Create config entry
                return self.async_create_entry(
                    title=user_input[CONF_AGENT_NAME],
                    data={
                        CONF_URL: self.discovered_url,
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_AGENT_NAME: user_input[CONF_AGENT_NAME],
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during zeroconf confirm: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=ZEROCONF_SCHEMA,
            errors=errors,
            description_placeholders={"url": self.discovered_url or ""},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "ChatterboxOptionsFlow":
        """Get the options flow for this config entry."""
        return ChatterboxOptionsFlow(config_entry)


class ChatterboxOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Chatterbox."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            try:
                # Test connection with potentially new URL and API key
                await _test_connection(user_input[CONF_URL], user_input[CONF_API_KEY])

                # Update config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        CONF_URL: user_input[CONF_URL],
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_AGENT_NAME: user_input[CONF_AGENT_NAME],
                    },
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during options flow: %s", err)
                errors["base"] = "unknown"

        # Populate form with current values
        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL, default=current_data.get(CONF_URL, "")): str,
                    vol.Optional(
                        CONF_API_KEY, default=current_data.get(CONF_API_KEY, "")
                    ): str,
                    vol.Optional(
                        CONF_AGENT_NAME,
                        default=current_data.get(CONF_AGENT_NAME, DEFAULT_AGENT_NAME),
                    ): str,
                }
            ),
            errors=errors,
        )
