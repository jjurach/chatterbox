"""Unit tests for chatterbox.conversation.zeroconf.

Tests Zeroconf/mDNS advertisement for the Chatterbox conversation server.
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, Mock, patch

import pytest

from chatterbox.conversation.zeroconf import ChatterboxZeroconf, get_local_ip


# ---------------------------------------------------------------------------
# Tests for get_local_ip()
# ---------------------------------------------------------------------------


def test_get_local_ip_returns_valid_ip() -> None:
    """Test that get_local_ip returns a valid IP address."""
    ip = get_local_ip()
    # Verify it's a valid IPv4 address
    assert isinstance(ip, str)
    parts = ip.split(".")
    assert len(parts) == 4
    for part in parts:
        assert part.isdigit()
        assert 0 <= int(part) <= 255


def test_get_local_ip_handles_socket_error() -> None:
    """Test that get_local_ip raises RuntimeError on socket error."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket_class.return_value.connect.side_effect = socket.error(
            "Connection failed"
        )
        with pytest.raises(RuntimeError, match="Unable to determine local IP"):
            get_local_ip()


def test_get_local_ip_handles_index_error() -> None:
    """Test that get_local_ip raises RuntimeError on IndexError."""
    with patch("socket.socket") as mock_socket_class:
        mock_instance = mock_socket_class.return_value
        mock_instance.getsockname.return_value = ()  # Empty tuple causes IndexError
        with pytest.raises(RuntimeError, match="Unable to determine local IP"):
            get_local_ip()


# ---------------------------------------------------------------------------
# Tests for ChatterboxZeroconf initialization
# ---------------------------------------------------------------------------


def test_zeroconf_init_default() -> None:
    """Test ChatterboxZeroconf initialization with defaults."""
    zc = ChatterboxZeroconf(port=8765)
    assert zc.port == 8765
    assert zc.version == "1.0"
    assert zc.service_info is None
    assert zc.zeroconf is None
    assert zc.registered is False


def test_zeroconf_init_custom_version() -> None:
    """Test ChatterboxZeroconf initialization with custom version."""
    zc = ChatterboxZeroconf(port=9000, version="2.0")
    assert zc.port == 9000
    assert zc.version == "2.0"


# ---------------------------------------------------------------------------
# Tests for ChatterboxZeroconf.start()
# ---------------------------------------------------------------------------


@patch("chatterbox.conversation.zeroconf.socket.gethostname")
@patch("chatterbox.conversation.zeroconf.socket.inet_aton")
@patch("chatterbox.conversation.zeroconf.get_local_ip")
@patch("chatterbox.conversation.zeroconf.Zeroconf")
def test_zeroconf_start_success(
    mock_zeroconf_class: Mock,
    mock_get_local_ip: Mock,
    mock_inet_aton: Mock,
    mock_gethostname: Mock,
) -> None:
    """Test successful Zeroconf service registration."""
    mock_get_local_ip.return_value = "192.168.1.100"
    mock_gethostname.return_value = "myhost"
    mock_inet_aton.return_value = b"\xc0\xa8\x01\x64"  # 192.168.1.100
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf_class.return_value = mock_zeroconf_instance

    zc = ChatterboxZeroconf(port=8765)
    zc.start()

    assert zc.registered is True
    assert zc.zeroconf is mock_zeroconf_instance
    assert zc.service_info is not None

    # Verify service info properties
    assert zc.service_info.type == "_chatterbox._tcp.local."
    assert "Chatterbox.myhost" in zc.service_info.name
    assert zc.service_info.port == 8765
    # Properties in zeroconf are accessed differently
    props = zc.service_info.properties
    assert props.get("version") == "1.0" or props.get(b"version") == b"1.0"
    assert props.get("api_path") == "/conversation" or props.get(b"api_path") == b"/conversation"

    # Verify register_service was called
    mock_zeroconf_instance.register_service.assert_called_once_with(zc.service_info)


@patch("chatterbox.conversation.zeroconf.socket.gethostname")
@patch("chatterbox.conversation.zeroconf.socket.inet_aton")
@patch("chatterbox.conversation.zeroconf.get_local_ip")
def test_zeroconf_start_get_local_ip_failure(
    mock_get_local_ip: Mock,
    mock_inet_aton: Mock,
    mock_gethostname: Mock,
) -> None:
    """Test that start() raises RuntimeError if get_local_ip fails."""
    mock_get_local_ip.side_effect = RuntimeError("Network error")

    zc = ChatterboxZeroconf(port=8765)
    with pytest.raises(RuntimeError, match="Failed to register Zeroconf service"):
        zc.start()

    assert zc.registered is False


@patch("chatterbox.conversation.zeroconf.socket.gethostname")
@patch("chatterbox.conversation.zeroconf.socket.inet_aton")
@patch("chatterbox.conversation.zeroconf.get_local_ip")
@patch("chatterbox.conversation.zeroconf.Zeroconf")
def test_zeroconf_start_zeroconf_exception(
    mock_zeroconf_class: Mock,
    mock_get_local_ip: Mock,
    mock_inet_aton: Mock,
    mock_gethostname: Mock,
) -> None:
    """Test that start() raises RuntimeError if Zeroconf registration fails."""
    mock_get_local_ip.return_value = "192.168.1.100"
    mock_gethostname.return_value = "myhost"
    mock_inet_aton.return_value = b"\xc0\xa8\x01\x64"
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf_instance.register_service.side_effect = Exception("Zeroconf error")
    mock_zeroconf_class.return_value = mock_zeroconf_instance

    zc = ChatterboxZeroconf(port=8765)
    with pytest.raises(RuntimeError, match="Failed to register Zeroconf service"):
        zc.start()

    assert zc.registered is False


def test_zeroconf_start_already_registered(
) -> None:
    """Test that start() is idempotent (warns if already registered)."""
    with patch("chatterbox.conversation.zeroconf.get_local_ip") as mock_get_ip:
        with patch("chatterbox.conversation.zeroconf.Zeroconf"):
            with patch("chatterbox.conversation.zeroconf.socket"):
                mock_get_ip.return_value = "192.168.1.100"

                zc = ChatterboxZeroconf(port=8765)
                zc.registered = True

                # Should warn and return early
                with patch("chatterbox.conversation.zeroconf.logger") as mock_logger:
                    zc.start()
                    mock_logger.warning.assert_called_once_with(
                        "Zeroconf service already registered"
                    )


# ---------------------------------------------------------------------------
# Tests for ChatterboxZeroconf.stop()
# ---------------------------------------------------------------------------


def test_zeroconf_stop_success() -> None:
    """Test successful Zeroconf service unregistration."""
    mock_zeroconf_instance = MagicMock()
    mock_service_info = MagicMock()

    zc = ChatterboxZeroconf(port=8765)
    zc.zeroconf = mock_zeroconf_instance
    zc.service_info = mock_service_info
    zc.registered = True

    zc.stop()

    assert zc.registered is False
    mock_zeroconf_instance.unregister_service.assert_called_once_with(mock_service_info)
    mock_zeroconf_instance.close.assert_called_once()


def test_zeroconf_stop_not_registered() -> None:
    """Test that stop() is safe when service not registered."""
    zc = ChatterboxZeroconf(port=8765)
    zc.registered = False

    # Should not raise
    with patch("chatterbox.conversation.zeroconf.logger") as mock_logger:
        zc.stop()
        mock_logger.debug.assert_called_once()


def test_zeroconf_stop_handles_unregister_exception() -> None:
    """Test that stop() handles exceptions during unregistration."""
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf_instance.unregister_service.side_effect = Exception("Unregister error")
    mock_service_info = MagicMock()

    zc = ChatterboxZeroconf(port=8765)
    zc.zeroconf = mock_zeroconf_instance
    zc.service_info = mock_service_info
    zc.registered = True

    # Should not raise, just log
    with patch("chatterbox.conversation.zeroconf.logger"):
        zc.stop()

    assert zc.registered is False


def test_zeroconf_stop_handles_close_exception() -> None:
    """Test that stop() handles exceptions during Zeroconf close."""
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf_instance.close.side_effect = Exception("Close error")
    mock_service_info = MagicMock()

    zc = ChatterboxZeroconf(port=8765)
    zc.zeroconf = mock_zeroconf_instance
    zc.service_info = mock_service_info
    zc.registered = True

    # Should not raise, just log
    with patch("chatterbox.conversation.zeroconf.logger"):
        zc.stop()

    assert zc.registered is False


# ---------------------------------------------------------------------------
# Integration tests (with real socket calls)
# ---------------------------------------------------------------------------


def test_zeroconf_full_lifecycle() -> None:
    """Test full start/stop lifecycle with mocked Zeroconf."""
    with patch("chatterbox.conversation.zeroconf.Zeroconf") as mock_zeroconf_class:
        with patch("chatterbox.conversation.zeroconf.get_local_ip") as mock_get_ip:
            with patch("chatterbox.conversation.zeroconf.socket.gethostname") as mock_hostname:
                with patch("chatterbox.conversation.zeroconf.socket.inet_aton") as mock_inet:
                    mock_instance = MagicMock()
                    mock_zeroconf_class.return_value = mock_instance
                    mock_get_ip.return_value = "192.168.1.100"
                    mock_hostname.return_value = "testhost"
                    mock_inet.return_value = b"\xc0\xa8\x01\x64"

                    zc = ChatterboxZeroconf(port=9999, version="1.5")

                    # Start
                    zc.start()
                    assert zc.registered is True
                    assert zc.service_info is not None
                    assert zc.zeroconf is mock_instance
                    assert zc.service_info.port == 9999

                    # Stop
                    zc.stop()
                    assert zc.registered is False
                    mock_instance.unregister_service.assert_called_once()
                    mock_instance.close.assert_called_once()
