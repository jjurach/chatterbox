"""
Tests for the Wyoming Voice Assistant Server with LangChain Integration.

This module contains pytest tests to verify that the TCP server
opens correctly and tests the LangChain agent with mocked Ollama responses.
"""

import asyncio
import socket
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def server_port() -> int:
    """Return the port the server should run on."""
    return 10700


@pytest.fixture
def server_host() -> str:
    """Return the host the server should bind to."""
    return "localhost"


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a TCP port is open and accepting connections.

    Args:
        host: The hostname or IP address to check
        port: The port number to check
        timeout: Connection timeout in seconds

    Returns:
        True if the port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


@pytest.mark.asyncio
async def test_server_tcp_port_opens(server_host: str, server_port: int) -> None:
    """
    Test that the Wyoming server opens a TCP port successfully.

    This test imports and starts the server, then verifies that
    the configured port is open and accepting connections.
    """
    # Import here to avoid import errors if wyoming is not installed
    try:
        from backend.src.main import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer(host=server_host, port=server_port)

    # Start the server in a task
    server_task = asyncio.create_task(server.run())

    try:
        # Give the server a moment to start
        await asyncio.sleep(1)

        # Check if the port is open
        assert is_port_open(
            server_host, server_port
        ), f"Server port {server_port} is not open"

    finally:
        # Clean up: cancel the server task
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


def test_port_configuration() -> None:
    """
    Test that the server uses the correct default port configuration.
    """
    try:
        from backend.src.main import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()
    assert server.port == 10700, "Default port should be 10700"
    assert server.host == "0.0.0.0", "Default host should be 0.0.0.0"


def test_custom_port_configuration() -> None:
    """
    Test that the server can be configured with custom host and port.
    """
    try:
        from backend.src.main import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    custom_host = "127.0.0.1"
    custom_port = 9999

    server = VoiceAssistantServer(host=custom_host, port=custom_port)
    assert server.host == custom_host
    assert server.port == custom_port


def test_get_time_tool() -> None:
    """
    Test that the get_time tool returns a valid time string.
    """
    try:
        from backend.src.main import get_time
    except ImportError:
        pytest.skip("Wyoming library not installed")

    time_str = get_time()
    assert isinstance(time_str, str)
    assert len(time_str) == 19  # Format: YYYY-MM-DD HH:MM:SS
    assert time_str[4] == "-" and time_str[7] == "-"  # Date format check
    assert time_str[10] == " " and time_str[13] == ":"  # Time format check


def test_langchain_agent_initialization() -> None:
    """
    Test that the LangChain agent is properly initialized with tools.
    """
    try:
        from backend.src.main import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()
    assert server.agent is not None
    assert server.memory is not None
    assert server.llm is not None
    # Verify the agent has access to the GetTime tool
    assert len(server.agent.tools) > 0
    tool_names = [tool.name for tool in server.agent.tools]
    assert "GetTime" in tool_names


@pytest.mark.asyncio
async def test_process_user_input_with_mocked_agent() -> None:
    """
    Test that user input is correctly processed through the LangChain agent.
    This test mocks the agent to avoid calling the actual Ollama service.
    """
    try:
        from backend.src.main import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()

    # Mock the agent's run method to avoid calling Ollama
    with patch.object(server.agent, "run", return_value="The time is 12:00:00"):
        response_event = await server._process_user_input("What is the current time?")

        # Verify the response is a Synthesize event with the agent's response
        assert response_event is not None
        assert hasattr(response_event, "text")
        assert "12:00:00" in response_event.text


@pytest.mark.asyncio
async def test_process_user_input_with_error_handling() -> None:
    """
    Test that errors during agent processing are properly handled.
    """
    try:
        from backend.src.main import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()

    # Mock the agent to raise an exception
    with patch.object(
        server.agent, "run", side_effect=Exception("Ollama connection failed")
    ):
        response_event = await server._process_user_input("What is the time?")

        # Verify error handling creates a proper response
        assert response_event is not None
        assert hasattr(response_event, "text")
        assert "error" in response_event.text.lower()
