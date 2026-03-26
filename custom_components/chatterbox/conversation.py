"""Chatterbox ConversationEntity for Home Assistant.

This module implements a ConversationEntity that proxies conversation turns
to a Chatterbox FastAPI server backend via HTTP.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from .const import CONF_AGENT_NAME, CONF_API_KEY, CONF_URL, DEFAULT_AGENT_NAME, DEFAULT_TIMEOUT, OFFLINE_MESSAGE, DOMAIN

if TYPE_CHECKING:
    from homeassistant.components.conversation import ConversationInput, ConversationResult
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _get_base_class():
    """Get the ConversationEntity base class, with fallback for testing."""
    try:
        from homeassistant.components.conversation import ConversationEntity
        from homeassistant.const import MATCH_ALL
        return ConversationEntity, MATCH_ALL
    except ImportError:
        # For testing without HA installed, use a simple base class
        class _FakeConversationEntity:
            pass
        return _FakeConversationEntity, "match_all"


_ConversationEntity, _MATCH_ALL = _get_base_class()


class ChatterboxAgent(_ConversationEntity):
    """Conversation entity that proxies to Chatterbox FastAPI server."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_key: str,
        agent_name: str = DEFAULT_AGENT_NAME,
    ) -> None:
        """Initialize the Chatterbox conversation agent.

        Args:
            hass: Home Assistant instance
            url: Base URL of the Chatterbox server (e.g. http://localhost:8765)
            api_key: API key for Bearer token authentication
            agent_name: Display name of the agent
        """
        self.hass = hass
        self._url = url
        self._api_key = api_key
        self._attr_name = agent_name
        self._attr_supported_languages = _MATCH_ALL

    async def async_process(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Process a conversation turn by calling the Chatterbox server.

        Args:
            user_input: The user's input (text, conversation_id, language)

        Returns:
            ConversationResult with the LLM's response text

        Raises:
            No exceptions; always returns a ConversationResult with either
            the LLM response or an offline/error message.
        """
        # Import ConversationResult at runtime to support testing
        from homeassistant.components.conversation import ConversationResult

        try:
            # Build request body
            request_body = {
                "text": user_input.text,
                "conversation_id": user_input.conversation_id,
                "language": user_input.language or "en",
            }

            # Prepare headers with Bearer auth
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            # Make HTTP request to the Chatterbox server
            async with aiohttp.ClientSession() as session:
                url = f"{self._url}/conversation"
                timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
                async with session.post(
                    url,
                    json=request_body,
                    headers=headers,
                    timeout=timeout,
                ) as resp:
                    if resp.status == 200:
                        # Success: parse response and return
                        data = await resp.json()
                        return ConversationResult(
                            response_text=data.get("response_text", ""),
                            conversation_id=data.get("conversation_id"),
                            extra=data.get("extra", {}),
                        )
                    elif resp.status == 401:
                        # Authentication error
                        _LOGGER.warning(
                            "Chatterbox authentication failed (HTTP 401) for %s",
                            self._url,
                        )
                        error_msg = "Authentication failed. Please check your API key."
                        return ConversationResult(
                            response_text=error_msg,
                            conversation_id=user_input.conversation_id,
                        )
                    else:
                        # Other HTTP errors
                        _LOGGER.warning(
                            "Chatterbox server error (HTTP %d) for %s: %s",
                            resp.status,
                            self._url,
                            await resp.text(),
                        )
                        return ConversationResult(
                            response_text=OFFLINE_MESSAGE,
                            conversation_id=user_input.conversation_id,
                        )

        except asyncio.TimeoutError:
            # Timeout error
            _LOGGER.warning(
                "Chatterbox request timed out (timeout=%ds) for %s",
                DEFAULT_TIMEOUT,
                self._url,
            )
            await self._fire_notification(
                "Chatterbox Timeout",
                f"Chatterbox server did not respond within {DEFAULT_TIMEOUT} seconds.",
            )
            return ConversationResult(
                response_text=OFFLINE_MESSAGE,
                conversation_id=user_input.conversation_id,
            )

        except aiohttp.ClientError as err:
            # Connection error
            _LOGGER.warning(
                "Chatterbox connection error for %s: %s",
                self._url,
                err,
            )
            await self._fire_notification(
                "Chatterbox Connection Error",
                f"Cannot connect to Chatterbox server at {self._url}. Error: {err}",
            )
            return ConversationResult(
                response_text=OFFLINE_MESSAGE,
                conversation_id=user_input.conversation_id,
            )

        except Exception as err:
            # Unexpected error
            _LOGGER.exception(
                "Unexpected error in ChatterboxAgent.async_process: %s",
                err,
            )
            await self._fire_notification(
                "Chatterbox Unexpected Error",
                f"An unexpected error occurred while processing your request: {err}",
            )
            return ConversationResult(
                response_text=OFFLINE_MESSAGE,
                conversation_id=user_input.conversation_id,
            )

    async def _fire_notification(self, title: str, message: str) -> None:
        """Fire a persistent notification in Home Assistant.

        Args:
            title: Notification title
            message: Notification message
        """
        try:
            from homeassistant.components.persistent_notification import async_create
            await async_create(
                self.hass,
                message=message,
                title=title,
                notification_id=f"{DOMAIN}_notification",
            )
        except Exception as err:
            _LOGGER.error("Failed to create persistent notification: %s", err)
