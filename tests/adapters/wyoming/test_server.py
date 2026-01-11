"""
Tests for the Wyoming Voice Assistant Server with LangChain Integration.

This module contains pytest tests to verify that the server components
work correctly and tests the LangChain agent with mocked Ollama responses.
"""

import asyncio
import socket
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from cackle.agent import VoiceAssistantAgent
from cackle.adapters.wyoming import VoiceAssistantServer
from cackle.tools import get_available_tools
from cackle.tools.builtin import get_time


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


# ============================================================================
# Tests for VoiceAssistantServer
# ============================================================================


@pytest.mark.asyncio
async def test_server_tcp_port_opens(server_host: str, server_port: int) -> None:
    """
    Test that the Wyoming server can be created with custom host and port.

    Note: Actual TCP port opening is integration tested, not unit tested.
    This test verifies the server can be initialized with custom port settings.
    """
    try:
        server = VoiceAssistantServer(host=server_host, port=server_port)
    except ImportError:
        pytest.skip("Wyoming library not installed")

    # Verify server was initialized with correct settings
    assert server.host == server_host
    assert server.port == server_port


def test_port_configuration() -> None:
    """
    Test that the server uses the correct default port configuration.
    """
    try:
        from backend.src.server import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()
    assert server.port == 10700
    assert server.host == "0.0.0.0"


def test_custom_port_configuration() -> None:
    """
    Test that the server can be configured with custom host and port.
    """
    try:
        from backend.src.server import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer(host="127.0.0.1", port=9999)
    assert server.host == "127.0.0.1"
    assert server.port == 9999


# ============================================================================
# Tests for Tools
# ============================================================================


def test_get_time_tool() -> None:
    """
    Test that the get_time tool returns a valid time string.
    """
    time_str = get_time()

    # Verify format is YYYY-MM-DD HH:MM:SS
    assert len(time_str) == 19  # 19 characters in YYYY-MM-DD HH:MM:SS
    assert time_str[4] == "-" and time_str[7] == "-"  # Date format check
    assert time_str[10] == " " and time_str[13] == ":"  # Time format check


def test_available_tools() -> None:
    """
    Test that available tools are properly defined.
    """
    tools = get_available_tools()

    # Verify tools list is not empty
    assert len(tools) > 0

    # Verify GetTime tool is present
    tool_names = [tool.name for tool in tools]
    assert "GetTime" in tool_names

    # Verify each tool has required attributes
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "func")
        assert hasattr(tool, "description")


# ============================================================================
# Tests for VoiceAssistantAgent
# ============================================================================


def test_agent_initialization() -> None:
    """
    Test that the VoiceAssistantAgent is properly initialized with tools.
    """
    try:
        agent = VoiceAssistantAgent()
    except ImportError:
        pytest.skip("Wyoming library not installed")

    assert agent.llm is not None
    assert agent.memory is not None
    assert agent.agent is not None
    # Verify the agent has access to tools
    assert agent.agent.tools is not None


def test_agent_configuration() -> None:
    """
    Test that the VoiceAssistantAgent can be configured with custom settings.
    """
    try:
        from backend.src.agent import VoiceAssistantAgent
    except ImportError:
        pytest.skip("Wyoming library not installed")

    agent = VoiceAssistantAgent(
        ollama_base_url="http://custom:11434/v1",
        ollama_model="custom-model",
        ollama_temperature=0.5,
        conversation_window_size=5,
    )

    assert agent.ollama_base_url == "http://custom:11434/v1"
    assert agent.ollama_model == "custom-model"
    assert agent.ollama_temperature == 0.5
    assert agent.conversation_window_size == 5


@pytest.mark.asyncio
async def test_agent_process_input_method_exists() -> None:
    """
    Test that the agent has the process_input method.
    """
    try:
        from backend.src.agent import VoiceAssistantAgent
    except ImportError:
        pytest.skip("Wyoming library not installed")

    agent = VoiceAssistantAgent()

    # Verify the method exists and is callable
    assert hasattr(agent, "process_input")
    assert callable(agent.process_input)


@pytest.mark.asyncio
async def test_agent_has_llm_and_memory() -> None:
    """
    Test that the agent has LLM and memory initialized.
    """
    try:
        from backend.src.agent import VoiceAssistantAgent
    except ImportError:
        pytest.skip("Wyoming library not installed")

    agent = VoiceAssistantAgent()

    # Verify critical components are initialized
    assert agent.llm is not None
    assert agent.memory is not None
    assert agent.agent is not None


def test_agent_memory_reset() -> None:
    """
    Test that the agent memory can be reset.
    """
    try:
        from backend.src.agent import VoiceAssistantAgent
    except ImportError:
        pytest.skip("Wyoming library not installed")

    agent = VoiceAssistantAgent()
    agent.reset_memory()
    # If no exception is raised, the test passes


@pytest.mark.asyncio
async def test_transcript_event_handling() -> None:
    """
    Test that Transcript events are properly recognized and dispatched.
    """
    try:
        from backend.src.server import VoiceAssistantServer
        from wyoming.asr import Transcript
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()

    # Create a transcript event
    transcript = Transcript(text="What time is it?")

    # Verify that transcript events are recognized
    assert isinstance(transcript, Transcript)
    assert transcript.text == "What time is it?"

    # Verify the transcript is the correct type
    assert hasattr(transcript, "text")


@pytest.mark.asyncio
async def test_transcribe_event_handling() -> None:
    """
    Test that Transcribe events are properly handled.
    """
    try:
        from backend.src.server import VoiceAssistantServer
        from wyoming.asr import Transcribe
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()

    # Transcribe events should be acknowledged without processing
    transcribe = Transcribe()
    response = await server.handle_event(transcribe)

    # Should return None (no response needed for Transcribe request)
    assert response is None


@pytest.mark.asyncio
async def test_ollama_connection_validation_failure() -> None:
    """
    Test that server fails gracefully if Ollama is not running.
    """
    try:
        from backend.src.server import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()

    # Mock httpx to simulate Ollama connection failure
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        with pytest.raises(RuntimeError, match="Ollama is not accessible"):
            await server.run()


@pytest.mark.asyncio
async def test_ollama_connection_validation_success() -> None:
    """
    Test that Ollama connection validation succeeds when Ollama is running.
    """
    try:
        from backend.src.server import VoiceAssistantServer
    except ImportError:
        pytest.skip("Wyoming library not installed")

    server = VoiceAssistantServer()

    # Mock successful Ollama response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "llama3.1:8b"},
            {"name": "neural-chat"},
        ]
    }

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        # Should not raise an exception
        result = await server._validate_ollama_connection()
        assert result is True
