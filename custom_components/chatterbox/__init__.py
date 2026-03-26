"""The Chatterbox integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import CONF_AGENT_NAME, CONF_API_KEY, CONF_URL, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Chatterbox from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this integration

    Returns:
        True if setup was successful
    """
    from homeassistant.components.conversation import async_set_agent

    from .conversation import ChatterboxAgent

    _LOGGER.debug("Setting up Chatterbox integration")

    # Store the entry in hass.data for later retrieval
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    # Create and register the conversation agent
    agent = ChatterboxAgent(
        hass=hass,
        url=entry.data.get(CONF_URL),
        api_key=entry.data.get(CONF_API_KEY, ""),
        agent_name=entry.data.get(CONF_AGENT_NAME, "Chatterbox"),
    )

    # Store agent reference in hass.data for later retrieval in async_unload_entry
    if "agent" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["agent"] = {}
    hass.data[DOMAIN]["agent"][entry.entry_id] = agent

    # Register the agent with HA's conversation platform
    await async_set_agent(hass, entry.entry_id, agent)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload was successful
    """
    from homeassistant.components.conversation import async_set_agent

    _LOGGER.debug("Unloading Chatterbox integration")

    # Unregister the conversation agent
    await async_set_agent(hass, entry.entry_id, None)

    # Clean up stored agent and entry
    if DOMAIN in hass.data:
        if "agent" in hass.data[DOMAIN] and entry.entry_id in hass.data[DOMAIN]["agent"]:
            del hass.data[DOMAIN]["agent"][entry.entry_id]
        if entry.entry_id in hass.data[DOMAIN]:
            del hass.data[DOMAIN][entry.entry_id]

    return True
