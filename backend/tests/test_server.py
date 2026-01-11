"""
Tests for the Wyoming Voice Assistant Server.

This module contains pytest tests to verify that the TCP server
opens correctly and is ready to accept connections.
"""

import asyncio
import socket
from typing import Generator

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
