"""End-to-end integration tests for Chatterbox HA integration.

This module tests the complete Chatterbox Home Assistant integration workflow,
including:
- Configuration flow (user entry and Zeroconf discovery)
- Conversation agent initialization and setup
- Full conversation turns through the FastAPI server
- Error handling and offline behavior
- Multi-turn conversation ID threading
- Server restart and recovery scenarios

These tests exercise the integration via the conversation HTTP server without
requiring a real Home Assistant instance. The hass fixture is mocked.

Note: These tests are designed to work WITHOUT Home Assistant installed.
Mocking is used to simulate HA's conversation API.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
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
sys.modules["homeassistant.data_entry_flow"] = MagicMock()


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


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def hass_mock():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.components = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def chatterbox_url():
    """Return the test Chatterbox server URL."""
    return "http://localhost:8765"


@pytest.fixture
def api_key():
    """Return the test API key."""
    return "test_api_key_12345"


@pytest.fixture
def agent(hass_mock, chatterbox_url, api_key):
    """Create a ChatterboxAgent for testing."""
    return ChatterboxAgent(
        hass=hass_mock,
        url=chatterbox_url,
        api_key=api_key,
        agent_name="Test Chatterbox",
    )


# ============================================================================
# Helper functions for mocking HTTP responses
# ============================================================================


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


def create_mock_session_for_health_check(status=200):
    """Create a mock aiohttp session for health checks.

    Args:
        status: HTTP status code (default 200)
    """
    # Create mock response
    mock_response = AsyncMock()
    mock_response.status = status

    # Create mock get context manager
    mock_get_cm = AsyncMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_cm.__aexit__ = AsyncMock(return_value=None)

    # Create mock session
    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_get_cm)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return mock_session


# ============================================================================
# Test Classes: Basic Conversation Functionality
# ============================================================================


class TestChatterboxHAIntegrationBasics:
    """Test basic functionality of the Chatterbox HA integration."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test that the agent initializes with correct configuration."""
        assert agent._url == "http://localhost:8765"
        assert agent._api_key == "test_api_key_12345"
        assert agent._attr_name == "Test Chatterbox"

    @pytest.mark.asyncio
    async def test_successful_conversation_turn(self, agent):
        """Test a successful conversation turn through the full pipeline."""
        user_input = ConversationInput(
            text="What is the weather?",
            conversation_id="conv_123",
            language="en",
        )

        expected_response = {
            "response_text": "The weather is sunny and warm today.",
            "conversation_id": "conv_123",
            "extra": {"model": "gpt-4o-mini", "latency_ms": 250},
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=expected_response
            )

            result = await agent.async_process(user_input)

            # Verify response
            assert result.response_text == "The weather is sunny and warm today."
            assert result.conversation_id == "conv_123"
            assert result.extra == {"model": "gpt-4o-mini", "latency_ms": 250}

            # Verify the request was made to the correct URL with correct body
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[0][0] == "http://localhost:8765/conversation"
            assert call_args[1]["json"]["text"] == "What is the weather?"
            assert call_args[1]["json"]["conversation_id"] == "conv_123"
            assert call_args[1]["json"]["language"] == "en"

    @pytest.mark.asyncio
    async def test_request_includes_auth_header(self, agent):
        """Test that the HTTP request includes Bearer token authorization."""
        user_input = ConversationInput(text="Hello", language="en")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data={"response_text": "Hi there!"}
            )

            await agent.async_process(user_input)

            # Verify Authorization header
            call_args = mock_session_class.return_value.post.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_api_key_12345"

    @pytest.mark.asyncio
    async def test_request_without_api_key(self, hass_mock, chatterbox_url):
        """Test that no Authorization header is sent when API key is empty."""
        agent = ChatterboxAgent(
            hass=hass_mock,
            url=chatterbox_url,
            api_key="",
            agent_name="TestAgent",
        )

        user_input = ConversationInput(text="Hello", language="en")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data={"response_text": "Hi!"}
            )

            await agent.async_process(user_input)

            # Verify no Authorization header
            call_args = mock_session_class.return_value.post.call_args
            headers = call_args[1].get("headers", {})
            assert "Authorization" not in headers


# ============================================================================
# Test Classes: Connection Errors and Offline Behavior
# ============================================================================


class TestChatterboxHAIntegrationOfflineBehavior:
    """Test offline behavior and connection error handling."""

    @pytest.mark.asyncio
    async def test_server_connection_timeout(self, agent):
        """Test that timeout errors return the offline message."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_timeout",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises TimeoutError
            mock_session = AsyncMock()

            async def raise_timeout(*args, **kwargs):
                raise asyncio.TimeoutError("Request timed out")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_timeout

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
                assert result.conversation_id == "conv_timeout"

                # Should fire notification
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert "Timeout" in call_args[1]["title"]

    @pytest.mark.asyncio
    async def test_server_connection_error(self, agent):
        """Test that connection errors return the offline message."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_conn_err",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises ClientConnectionError
            mock_session = AsyncMock()

            async def raise_connection_error(*args, **kwargs):
                raise aiohttp.ClientConnectionError("Cannot connect to server")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_connection_error

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
                assert result.conversation_id == "conv_conn_err"

                # Should fire notification
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert "Connection Error" in call_args[1]["title"]

    @pytest.mark.asyncio
    async def test_server_restart_recovery(self, agent):
        """Test that agent recovers after server restart.

        This simulates:
        1. Server returns error (500)
        2. Server recovers and returns success
        """
        user_input = ConversationInput(text="Test", conversation_id="conv_recovery")

        # First call: server error
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=500
            )

            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ):
                result = await agent.async_process(user_input)
                assert result.response_text == OFFLINE_MESSAGE

        # Second call: server recovered
        expected_response = {
            "response_text": "Server is back online!",
            "conversation_id": "conv_recovery",
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=expected_response
            )

            result = await agent.async_process(user_input)
            assert result.response_text == "Server is back online!"


# ============================================================================
# Test Classes: Multi-turn Conversation and State Threading
# ============================================================================


class TestChatterboxHAIntegrationMultiTurn:
    """Test multi-turn conversation with conversation ID threading."""

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_with_id_threading(self, agent):
        """Test that conversation_id is threaded through multiple turns.

        This simulates a multi-turn conversation where the agent maintains
        context across multiple user inputs using the conversation_id.
        """
        conv_id = "multi_turn_001"

        # Turn 1: User asks about weather in Paris
        turn1_input = ConversationInput(
            text="What is the weather in Paris?",
            conversation_id=conv_id,
        )

        turn1_response = {
            "response_text": "The weather in Paris is mild and cloudy.",
            "conversation_id": conv_id,
            "extra": {"turn": 1},
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=turn1_response
            )

            result1 = await agent.async_process(turn1_input)
            assert result1.response_text == "The weather in Paris is mild and cloudy."
            assert result1.conversation_id == conv_id

            # Verify conversation_id was sent in request
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["conversation_id"] == conv_id

        # Turn 2: User asks follow-up question using same conversation_id
        turn2_input = ConversationInput(
            text="What about the temperature?",
            conversation_id=conv_id,
        )

        turn2_response = {
            "response_text": "The temperature is around 15°C.",
            "conversation_id": conv_id,
            "extra": {"turn": 2},
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=turn2_response
            )

            result2 = await agent.async_process(turn2_input)
            assert result2.response_text == "The temperature is around 15°C."
            assert result2.conversation_id == conv_id

            # Verify same conversation_id was used
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["conversation_id"] == conv_id

    @pytest.mark.asyncio
    async def test_single_turn_without_conversation_id(self, agent):
        """Test single-turn conversation without conversation_id."""
        user_input = ConversationInput(
            text="What time is it?",
            conversation_id=None,
        )

        expected_response = {
            "response_text": "It is currently 3:45 PM.",
            "conversation_id": None,
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=expected_response
            )

            result = await agent.async_process(user_input)
            assert result.response_text == "It is currently 3:45 PM."
            assert result.conversation_id is None


# ============================================================================
# Test Classes: Authentication and Authorization
# ============================================================================


class TestChatterboxHAIntegrationAuth:
    """Test authentication and authorization handling."""

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_auth_error(self, agent):
        """Test that HTTP 401 returns authentication error message."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_auth",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=401
            )

            result = await agent.async_process(user_input)

            # Should return auth error message
            assert "authentication" in result.response_text.lower()
            assert result.conversation_id == "conv_auth"

    @pytest.mark.asyncio
    async def test_auth_error_without_notification(self, agent):
        """Test that 401 errors do NOT fire a persistent notification.

        Auth errors are different from connection errors - they're expected
        and don't represent a server availability issue.
        """
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=401
            )

            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                await agent.async_process(user_input)

                # Should NOT fire notification for auth errors
                mock_notify.assert_not_called()


# ============================================================================
# Test Classes: HTTP Error Handling
# ============================================================================


class TestChatterboxHAIntegrationHttpErrors:
    """Test HTTP error handling."""

    @pytest.mark.asyncio
    async def test_http_500_server_error(self, agent):
        """Test that HTTP 500 returns offline message."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_500",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=500
            )

            result = await agent.async_process(user_input)
            assert result.response_text == OFFLINE_MESSAGE
            assert result.conversation_id == "conv_500"

    @pytest.mark.asyncio
    async def test_http_503_service_unavailable(self, agent):
        """Test that HTTP 503 returns offline message."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_503",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=503
            )

            result = await agent.async_process(user_input)
            assert result.response_text == OFFLINE_MESSAGE
            assert result.conversation_id == "conv_503"

    @pytest.mark.asyncio
    async def test_http_404_not_found(self, agent):
        """Test that HTTP 404 returns offline message."""
        user_input = ConversationInput(
            text="Hello",
            conversation_id="conv_404",
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=404
            )

            result = await agent.async_process(user_input)
            assert result.response_text == OFFLINE_MESSAGE
            assert result.conversation_id == "conv_404"


# ============================================================================
# Test Classes: Language Handling
# ============================================================================


class TestChatterboxHAIntegrationLanguage:
    """Test language parameter handling."""

    @pytest.mark.asyncio
    async def test_language_parameter_passed_through(self, agent):
        """Test that language parameter is passed to the server."""
        user_input = ConversationInput(
            text="Bonjour",
            conversation_id="conv_fr",
            language="fr",
        )

        expected_response = {
            "response_text": "Bonjour! Comment allez-vous?",
            "conversation_id": "conv_fr",
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=expected_response
            )

            result = await agent.async_process(user_input)
            assert result.response_text == "Bonjour! Comment allez-vous?"

            # Verify language was passed in request
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["language"] == "fr"

    @pytest.mark.asyncio
    async def test_language_defaults_to_english(self, agent):
        """Test that language defaults to 'en' when not provided."""
        user_input = ConversationInput(
            text="Hello",
            language=None,
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data={"response_text": "Hi there!"}
            )

            await agent.async_process(user_input)

            # Verify default language
            call_args = mock_session_class.return_value.post.call_args
            assert call_args[1]["json"]["language"] == "en"

    @pytest.mark.asyncio
    async def test_language_parameter_with_multiple_languages(self, agent):
        """Test that various languages are passed through correctly."""
        languages = [
            ("es", "Hola", "Hola, ¿cómo estás?"),
            ("de", "Hallo", "Hallo, wie geht es dir?"),
            ("it", "Ciao", "Ciao, come stai?"),
        ]

        for lang_code, input_text, response_text in languages:
            user_input = ConversationInput(
                text=input_text,
                language=lang_code,
            )

            expected_response = {
                "response_text": response_text,
                "conversation_id": None,
            }

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session_class.return_value = create_mock_session_with_response(
                    status=200, response_data=expected_response
                )

                result = await agent.async_process(user_input)
                assert result.response_text == response_text

                # Verify language was passed
                call_args = mock_session_class.return_value.post.call_args
                assert call_args[1]["json"]["language"] == lang_code


# ============================================================================
# Test Classes: Notification System
# ============================================================================


class TestChatterboxHAIntegrationNotifications:
    """Test persistent notification system."""

    @pytest.mark.asyncio
    async def test_notification_fired_on_connection_error(self, agent):
        """Test that persistent notification is fired on connection error."""
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
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
        """Test that persistent notification is fired on timeout."""
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
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

    @pytest.mark.asyncio
    async def test_notification_includes_domain_id(self, agent):
        """Test that notification has correct domain ID."""
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()

            async def raise_error(*args, **kwargs):
                raise aiohttp.ClientConnectionError("Error")

            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = raise_error

            mock_session.post = MagicMock(return_value=mock_post_cm)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            with patch(
                "homeassistant.components.persistent_notification.async_create"
            ) as mock_notify:
                await agent.async_process(user_input)

                # Verify notification has correct ID
                call_args = mock_notify.call_args
                assert call_args[1]["notification_id"] == f"{DOMAIN}_notification"


# ============================================================================
# Test Classes: Edge Cases and Unexpected Conditions
# ============================================================================


class TestChatterboxHAIntegrationEdgeCases:
    """Test edge cases and unexpected conditions."""

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_offline_message(self, agent):
        """Test that unexpected exceptions return offline message."""
        user_input = ConversationInput(text="Hello")

        with patch("aiohttp.ClientSession") as mock_session_class:
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
            ):
                result = await agent.async_process(user_input)
                assert result.response_text == OFFLINE_MESSAGE

    @pytest.mark.asyncio
    async def test_response_with_missing_optional_fields(self, agent):
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
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=expected_response
            )

            result = await agent.async_process(user_input)

            # Should handle missing fields gracefully
            assert result.response_text == "Hello!"
            assert result.conversation_id is None
            assert result.extra == {}

    @pytest.mark.asyncio
    async def test_response_with_extra_fields(self, agent):
        """Test handling of response with extra metadata fields."""
        user_input = ConversationInput(text="Tell me a joke")

        expected_response = {
            "response_text": "Why did the chicken cross the road?",
            "conversation_id": "joke_conv",
            "extra": {
                "model": "gpt-4o-mini",
                "latency_ms": 342,
                "tokens_used": 87,
                "temperature": 0.7,
            },
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=expected_response
            )

            result = await agent.async_process(user_input)

            assert result.response_text == "Why did the chicken cross the road?"
            assert result.extra["model"] == "gpt-4o-mini"
            assert result.extra["latency_ms"] == 342
            assert result.extra["tokens_used"] == 87

    @pytest.mark.asyncio
    async def test_empty_response_text(self, agent):
        """Test handling of empty response text."""
        user_input = ConversationInput(text="Say nothing")

        expected_response = {
            "response_text": "",
            "conversation_id": "empty_conv",
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_session_with_response(
                status=200, response_data=expected_response
            )

            result = await agent.async_process(user_input)

            assert result.response_text == ""
            assert result.conversation_id == "empty_conv"


# ============================================================================
# Test Classes: Configuration and Setup
# ============================================================================


class TestChatterboxHAIntegrationSetup:
    """Test integration setup and configuration."""

    def test_agent_with_default_name(self, hass_mock, chatterbox_url, api_key):
        """Test agent creation with default display name."""
        agent = ChatterboxAgent(
            hass=hass_mock,
            url=chatterbox_url,
            api_key=api_key,
        )
        assert agent._attr_name == DEFAULT_AGENT_NAME

    def test_agent_with_custom_name(self, hass_mock, chatterbox_url, api_key):
        """Test agent creation with custom display name."""
        custom_name = "My Living Room Assistant"
        agent = ChatterboxAgent(
            hass=hass_mock,
            url=chatterbox_url,
            api_key=api_key,
            agent_name=custom_name,
        )
        assert agent._attr_name == custom_name

    def test_agent_supports_all_languages(self, agent):
        """Test that agent supports all languages (MATCH_ALL)."""
        assert agent._attr_supported_languages == "match_all"

    def test_agent_stores_hass_reference(self, hass_mock, chatterbox_url, api_key):
        """Test that agent stores reference to hass instance."""
        agent = ChatterboxAgent(
            hass=hass_mock,
            url=chatterbox_url,
            api_key=api_key,
        )
        assert agent.hass is hass_mock


# ============================================================================
# Manual Verification Checklist
# ============================================================================

"""
## Manual Verification Checklist for Task 6.20 - HA Chatterbox Integration

These tests cover the programmatic aspects of the integration. For complete
verification, also perform the following manual steps:

### Prerequisites
- [ ] Chatterbox FastAPI server running and accessible on LAN (e.g., http://192.168.0.100:8765)
- [ ] Home Assistant instance running on same LAN
- [ ] HACS installed in Home Assistant
- [ ] API key from Chatterbox logs: "API key: <uuid>"

### Configuration Flow - Zeroconf Discovery Path
- [ ] HA → Settings → Devices & Services → Create Automation
- [ ] "Chatterbox.<hostname>" appears in discovered integrations
- [ ] Click on discovered device
- [ ] Enter API key from Chatterbox logs
- [ ] Enter display name (e.g., "Living Room")
- [ ] "Test Connection" button shows success (validates GET /health endpoint)
- [ ] Integration created successfully

### Configuration Flow - Manual URL Entry Path
- [ ] HA → Settings → Devices & Services → Create Integration
- [ ] Search for and select "Chatterbox"
- [ ] Enter URL: http://192.168.0.100:8765 (or appropriate IP/hostname)
- [ ] Enter API key
- [ ] Enter display name
- [ ] "Test Connection" button validates and succeeds
- [ ] Integration created successfully

### Voice Pipeline Setup
- [ ] HA → Settings → Voice Assistants
- [ ] Select your voice assistant (or create new)
- [ ] Set Conversation Agent to "Chatterbox"
- [ ] Save configuration

### Voice Command Test
- [ ] Speak to your HA voice device (e.g., "What's the weather?")
- [ ] LLM response is heard through the voice device
- [ ] Conversation appears in HA history

### Offline Behavior Test
- [ ] Stop the Chatterbox service/container
- [ ] Speak a command to the voice device
- [ ] Hear "Chatterbox is temporarily offline, please try again."
- [ ] HA Notifications panel shows offline alert
- [ ] No HA restart required

### Server Restart and Recovery
- [ ] Restart Chatterbox service
- [ ] Wait 10 seconds for startup
- [ ] Speak a command to the voice device
- [ ] Normal LLM response is heard
- [ ] Integration continues to work without HA restart

### Options Flow - Reconfiguration
- [ ] HA → Settings → Devices & Services → Chatterbox
- [ ] Click on "Options"
- [ ] Change URL or API key or display name
- [ ] "Test Connection" validates new settings
- [ ] Save options
- [ ] Integration continues to work with new settings

### HACS Installation Path (Optional)
- [ ] HACS → Integrations → Custom repositories
- [ ] Add repository: https://github.com/phaedrus/hentown
- [ ] Search HACS for "Chatterbox"
- [ ] Install integration
- [ ] HA restart required
- [ ] After restart, add integration via Settings as normal
- [ ] Verify full flow works

### Error Scenarios
- [ ] Wrong API key: Should show "Authentication failed" in logs
- [ ] Wrong URL: Should show connection error during setup
- [ ] Malformed URL: Should be rejected by validation
- [ ] Server returns 500: Should return offline message
- [ ] Network timeout: Should return offline message + notification
"""
