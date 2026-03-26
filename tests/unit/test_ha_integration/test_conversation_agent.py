"""Tests for Chatterbox ConversationEntity.

These tests verify the conversation agent's ability to:
- Process successful conversation turns
- Handle connection errors gracefully
- Handle authentication errors (HTTP 401)
- Thread conversation IDs through multi-turn conversations
- Return appropriate error messages when offline
- Fire persistent notifications on connection failures

Note: These tests are designed to work in environments where HomeAssistant
is not installed. They mock the HomeAssistant components and imports.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# ============================================================================
# Mock homeassistant modules BEFORE importing anything from custom_components
# ============================================================================

# Create a fake homeassistant package structure
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.conversation"] = MagicMock()
sys.modules["homeassistant.components.persistent_notification"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()


# Define mock dataclasses for ConversationInput and ConversationResult
@dataclass
class ConversationInput:
    """Mock ConversationInput."""

    text: str
    conversation_id: str | None = None
    language: str | None = None


@dataclass
class ConversationResult:
    """Mock ConversationResult."""

    response_text: str
    conversation_id: str | None = None
    extra: dict = field(default_factory=dict)


# Setup mocks
sys.modules["homeassistant.components.conversation"].ConversationInput = ConversationInput
sys.modules["homeassistant.components.conversation"].ConversationResult = ConversationResult
sys.modules["homeassistant.components.conversation"].ConversationEntity = object
sys.modules["homeassistant.components.persistent_notification"].async_create = AsyncMock()
sys.modules["homeassistant.const"].MATCH_ALL = "match_all"

# Now we can import the agent
from custom_components.chatterbox.conversation import ChatterboxAgent
from custom_components.chatterbox.const import (
    CONF_AGENT_NAME,
    CONF_API_KEY,
    CONF_URL,
    DEFAULT_AGENT_NAME,
    DEFAULT_TIMEOUT,
    OFFLINE_MESSAGE,
    DOMAIN,
)


@pytest.fixture
def hass_mock():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.components = MagicMock()
    return hass


@pytest.fixture
def agent(hass_mock):
    """Create a ChatterboxAgent for testing."""
    return ChatterboxAgent(
        hass=hass_mock,
        url="http://localhost:8765",
        api_key="test_api_key",
        agent_name="TestChatterbox",
    )


def create_mock_session_with_response(status=200, response_data=None, json_error=None):
    """Create a mock aiohttp session that returns the given response.

    Args:
        status: HTTP status code (default 200)
        response_data: dict of response data for json() method
        json_error: Exception to raise from json() method
    """
    # Create mock response
    mock_response = AsyncMock()
    mock_response.status = status

    if json_error:
        mock_response.json = AsyncMock(side_effect=json_error)
    elif response_data is not None:
        mock_response.json = AsyncMock(return_value=response_data)
    else:
        mock_response.json = AsyncMock(return_value={})

    # Mock text method to return response data as string for logging
    if response_data and isinstance(response_data, dict):
        text_value = json.dumps(response_data)
    else:
        text_value = "Server error"

    mock_response.text = AsyncMock(return_value=text_value)

    # Create mock post context manager
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_cm.__aexit__ = AsyncMock(return_value=None)

    # Create mock session
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_post_cm)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return mock_session


class TestChatterboxAgentInit:
    """Test agent initialization."""

    def test_agent_init_with_defaults(self, hass_mock):
        """Test agent initialization with defaults."""
        agent = ChatterboxAgent(
            hass=hass_mock,
            url="http://localhost:8765",
            api_key="test_key",
        )
        assert agent._url == "http://localhost:8765"
        assert agent._api_key == "test_key"
        assert agent._attr_name == DEFAULT_AGENT_NAME
        assert agent._attr_supported_languages == "match_all"

    def test_agent_init_with_custom_name(self, hass_mock):
        """Test agent initialization with custom name."""
        agent = ChatterboxAgent(
            hass=hass_mock,
            url="http://localhost:8765",
            api_key="test_key",
            agent_name="CustomAgent",
        )
        assert agent._attr_name == "CustomAgent"

    def test_agent_init_stores_config(self, hass_mock):
        """Test that agent stores all configuration."""
        url = "http://192.168.1.100:9000"
        api_key = "secret_key_123"
        name = "MyAgent"

        agent = ChatterboxAgent(
            hass=hass_mock,
            url=url,
            api_key=api_key,
            agent_name=name,
        )

        assert agent._url == url
        assert agent._api_key == api_key
        assert agent._attr_name == name


class TestChatterboxAgentSuccessfulConversation:
    """Test successful conversation turns."""

    @pytest.mark.asyncio
    async def test_process_successful_turn(self, agent):
        """Test a successful conversation turn."""
        user_input = ConversationInput(
            text="What is the weather?",
            conversation_id="conv_123",
            language="en",
        )

        expected_response = {
            "response_text": "The weather is sunny.",
            "conversation_id": "conv_123",
            "extra": {"model": "gpt-4o-mini", "latency_ms": 250},
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=200, response_data=expected_response)

            result = await agent.async_process(user_input)

            # Verify response
            assert result.response_text == "The weather is sunny."
            assert result.conversation_id == "conv_123"
            assert result.extra == {"model": "gpt-4o-mini", "latency_ms": 250}

    @pytest.mark.asyncio
    async def test_process_without_conversation_id(self, agent):
        """Test conversation turn without conversation ID (single-turn)."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id=None,
            language="en",
        )

        expected_response = {
            "response_text": "Hello there!",
            "conversation_id": None,
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=200, response_data=expected_response)
            result = await agent.async_process(user_input)

            assert result.response_text == "Hello there!"
            assert result.conversation_id is None

    @pytest.mark.asyncio
    async def test_process_without_api_key(self, hass_mock):
        """Test conversation with no API key (unauthenticated)."""
        agent = ChatterboxAgent(
            hass=hass_mock,
            url="http://localhost:8765",
            api_key="",
            agent_name="TestAgent",
        )

        user_input = ConversationInput(
            text="Hello",
            language="en",
        )

        expected_response = {
            "response_text": "Hello!",
            "conversation_id": None,
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=200, response_data=expected_response)
            result = await agent.async_process(user_input)

            # Verify Authorization header is NOT included
            call_args = mock_session_class.return_value.post.call_args
            assert "Authorization" not in call_args[1]["headers"]


class TestChatterboxAgentConnectionErrors:
    """Test connection error handling."""

    @pytest.mark.asyncio
    async def test_process_connection_timeout(self, agent):
        """Test timeout during connection."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_123",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises on __aenter__
            mock_session = AsyncMock()

            async def raise_timeout(*args, **kwargs):
                raise asyncio.TimeoutError("Request timed out")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_timeout

            mock_session.post = MagicMock(return_value=mock_post_cm)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            # Mock the notification creation
            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                result = await agent.async_process(user_input)

                # Should return offline message
                assert result.response_text == OFFLINE_MESSAGE
                assert result.conversation_id == "conv_123"

                # Should fire notification
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert "timeout" in call_args[1]["title"].lower()

    @pytest.mark.asyncio
    async def test_process_connection_error(self, agent):
        """Test connection error (e.g., server unreachable)."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_456",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises on __aenter__
            mock_session = AsyncMock()

            async def raise_connection_error(*args, **kwargs):
                raise aiohttp.ClientConnectionError("Cannot connect to server")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_connection_error

            mock_session.post = MagicMock(return_value=mock_post_cm)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            # Mock the notification creation
            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                result = await agent.async_process(user_input)

                # Should return offline message
                assert result.response_text == OFFLINE_MESSAGE
                assert result.conversation_id == "conv_456"

                # Should fire notification
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert "connection" in call_args[1]["title"].lower()

    @pytest.mark.asyncio
    async def test_process_general_client_error(self, agent):
        """Test general aiohttp client error."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_789",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises on __aenter__
            mock_session = AsyncMock()

            async def raise_client_error(*args, **kwargs):
                raise aiohttp.ClientError("General error")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_client_error

            mock_session.post = MagicMock(return_value=mock_post_cm)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            # Mock the notification creation
            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                result = await agent.async_process(user_input)

                # Should return offline message
                assert result.response_text == OFFLINE_MESSAGE
                assert result.conversation_id == "conv_789"

                # Should fire notification
                mock_notify.assert_called_once()


class TestChatterboxAgentAuthenticationErrors:
    """Test authentication error handling."""

    @pytest.mark.asyncio
    async def test_process_http_401_auth_error(self, agent):
        """Test HTTP 401 authentication error."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_auth",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=401)
            result = await agent.async_process(user_input)

            # Should return auth error message
            assert "authentication" in result.response_text.lower()
            assert result.conversation_id == "conv_auth"


class TestChatterboxAgentHttpErrors:
    """Test HTTP error handling."""

    @pytest.mark.asyncio
    async def test_process_http_500_server_error(self, agent):
        """Test HTTP 500 server error."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_500",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=500)
            result = await agent.async_process(user_input)

            # Should return offline message
            assert result.response_text == OFFLINE_MESSAGE
            assert result.conversation_id == "conv_500"

    @pytest.mark.asyncio
    async def test_process_http_503_unavailable(self, agent):
        """Test HTTP 503 service unavailable."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_503",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=503)
            result = await agent.async_process(user_input)

            # Should return offline message
            assert result.response_text == OFFLINE_MESSAGE
            assert result.conversation_id == "conv_503"


class TestChatterboxAgentMultiTurn:
    """Test multi-turn conversation with conversation ID threading."""

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_id_threading(self, agent):
        """Test that conversation_id is threaded through multi-turn conversation."""
        conv_id = "multi_turn_session_001"

        # First turn
        user_input_1 = ConversationInput(
            text="What is the capital of France?",
            conversation_id=conv_id,
        )

        response_1 = {
            "response_text": "Paris is the capital of France.",
            "conversation_id": conv_id,
            "extra": {"turn": 1},
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(response_data=response_1)
            result_1 = await agent.async_process(user_input_1)

            # Verify first turn
            assert result_1.response_text == "Paris is the capital of France."
            assert result_1.conversation_id == conv_id

            # Check that conversation_id was in request
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["conversation_id"] == conv_id

        # Second turn with same conversation_id
        user_input_2 = ConversationInput(
            text="What is its population?",
            conversation_id=conv_id,
        )

        response_2 = {
            "response_text": "Paris has a population of approximately 2.1 million.",
            "conversation_id": conv_id,
            "extra": {"turn": 2},
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(response_data=response_2)
            result_2 = await agent.async_process(user_input_2)

            # Verify second turn
            assert result_2.response_text == "Paris has a population of approximately 2.1 million."
            assert result_2.conversation_id == conv_id

            # Check that same conversation_id was used in second request
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["conversation_id"] == conv_id


class TestChatterboxAgentLanguage:
    """Test language parameter handling."""

    @pytest.mark.asyncio
    async def test_process_with_language(self, agent):
        """Test that language is passed through correctly."""
        user_input = ConversationInput(
            text="Bonjour",
            conversation_id="conv_fr",
            language="fr",
        )

        expected_response = {
            "response_text": "Bonjour!",
            "conversation_id": "conv_fr",
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=200, response_data=expected_response)
            result = await agent.async_process(user_input)

            # Verify language was passed
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["language"] == "fr"

    @pytest.mark.asyncio
    async def test_process_defaults_language_to_en(self, agent):
        """Test that language defaults to 'en' if not provided."""
        user_input = ConversationInput(
            text="Hello",
            language=None,
        )

        expected_response = {
            "response_text": "Hello!",
            "conversation_id": None,
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=200, response_data=expected_response)
            result = await agent.async_process(user_input)

            # Verify language defaults to 'en'
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["language"] == "en"


class TestChatterboxAgentNotifications:
    """Test persistent notification handling."""

    @pytest.mark.asyncio
    async def test_notification_fired_on_connection_error(self, agent):
        """Test that a persistent notification is fired on connection error."""
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises on __aenter__
            mock_session = AsyncMock()

            async def raise_connection_error(*args, **kwargs):
                raise aiohttp.ClientConnectionError("Connection refused")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_connection_error

            mock_session.post = MagicMock(return_value=mock_post_cm)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                await agent.async_process(user_input)

                # Verify notification was created
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert call_args[0][0] == agent.hass
                assert "Connection Error" in call_args[1]["title"]
                assert "localhost" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_notification_fired_on_timeout(self, agent):
        """Test that a persistent notification is fired on timeout."""
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises on __aenter__
            mock_session = AsyncMock()

            async def raise_timeout(*args, **kwargs):
                raise asyncio.TimeoutError("Timeout")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_timeout

            mock_session.post = MagicMock(return_value=mock_post_cm)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                await agent.async_process(user_input)

                # Verify notification was created
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert "Timeout" in call_args[1]["title"]


class TestChatterboxAgentEdgeCases:
    """Test edge cases and unexpected conditions."""

    @pytest.mark.asyncio
    async def test_process_unexpected_exception(self, agent):
        """Test handling of unexpected exceptions."""
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises on __aenter__
            mock_session = AsyncMock()

            async def raise_value_error(*args, **kwargs):
                raise ValueError("Unexpected error")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_value_error

            mock_session.post = MagicMock(return_value=mock_post_cm)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                result = await agent.async_process(user_input)

                # Should return offline message
                assert result.response_text == OFFLINE_MESSAGE

                # Should fire notification
                mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_response_missing_fields(self, agent):
        """Test handling of response with missing optional fields."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_partial",
        )

        # Response with minimal fields
        expected_response = {
            "response_text": "Hello!",
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(status=200, response_data=expected_response)
            result = await agent.async_process(user_input)

            # Should handle missing fields gracefully
            assert result.response_text == "Hello!"
            assert result.conversation_id is None
            assert result.extra == {}
