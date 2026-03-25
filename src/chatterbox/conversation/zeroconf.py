"""Zeroconf/mDNS advertisement for Chatterbox conversation server.

This module handles advertising the Chatterbox conversation server on the LAN
via Zeroconf (mDNS) so that Home Assistant and other clients can auto-discover
it without manual IP/port configuration.

Service Type: _chatterbox._tcp.local.
Service Name: Chatterbox.<hostname>._chatterbox._tcp.local.

Example Properties:
    - version: 1.0
    - api_path: /conversation
"""

from __future__ import annotations

import logging
import socket
from typing import Optional

from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get the local IP address for Zeroconf advertisement.

    Uses a socket connection to a remote address (Google DNS) to determine
    the local IP without actually connecting. This works across different
    network configurations (WiFi, Ethernet, etc.).

    Returns:
        Local IP address as a string (e.g., "192.168.1.100").

    Raises:
        RuntimeError: If unable to determine local IP address.
    """
    try:
        # Create a socket and connect to Google DNS (doesn't actually connect)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except (socket.error, IndexError) as e:
        raise RuntimeError(f"Unable to determine local IP address: {e}") from e


class ChatterboxZeroconf:
    """Manages Zeroconf/mDNS advertisement for the Chatterbox conversation server.

    Attributes:
        service_info: ServiceInfo object describing the Chatterbox service.
        zeroconf: Zeroconf instance for registration/unregistration.
        registered: Whether the service is currently registered.
    """

    def __init__(self, port: int, version: str = "1.0") -> None:
        """Initialize Zeroconf advertisement.

        Args:
            port: Port number the conversation server listens on.
            version: API version string (default "1.0").
        """
        self.port = port
        self.version = version
        self.service_info: Optional[ServiceInfo] = None
        self.zeroconf: Optional[Zeroconf] = None
        self.registered = False

    def start(self) -> None:
        """Register the Chatterbox service on the local network.

        Advertises the service as:
            Name: Chatterbox.<hostname>._chatterbox._tcp.local.
            Type: _chatterbox._tcp.local.
            Port: self.port
            Properties:
                - version: API version (e.g., "1.0")
                - api_path: /conversation

        Raises:
            RuntimeError: If unable to get local IP or register service.
        """
        if self.registered:
            logger.warning("Zeroconf service already registered")
            return

        try:
            # Get local IP and hostname
            local_ip = get_local_ip()
            hostname = socket.gethostname()

            # Create service info
            service_name = f"Chatterbox.{hostname}._chatterbox._tcp.local."
            self.service_info = ServiceInfo(
                "_chatterbox._tcp.local.",
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties={
                    "version": self.version,
                    "api_path": "/conversation",
                },
            )

            # Create and start Zeroconf
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)
            self.registered = True

            logger.info(
                "Zeroconf service registered: %s (IP: %s, Port: %d)",
                service_name,
                local_ip,
                self.port,
            )
        except Exception as e:
            logger.error("Failed to register Zeroconf service: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to register Zeroconf service: {e}") from e

    def stop(self) -> None:
        """Unregister the Zeroconf service and clean up resources.

        This should be called during server shutdown to gracefully withdraw
        the service advertisement from the local network.
        """
        if not self.registered:
            logger.debug("Zeroconf service not registered, nothing to unregister")
            return

        try:
            if self.service_info and self.zeroconf:
                self.zeroconf.unregister_service(self.service_info)
                logger.info("Zeroconf service unregistered: %s", self.service_info.name)

            if self.zeroconf:
                self.zeroconf.close()
                logger.info("Zeroconf instance closed")
        except Exception as e:
            logger.error("Error during Zeroconf shutdown: %s", e, exc_info=True)
        finally:
            self.registered = False
