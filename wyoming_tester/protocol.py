"""Wyoming protocol connection and event handling."""

import asyncio
import logging
import socket
from typing import Any, Optional
from urllib.parse import urlparse

try:
    from wyoming.audio import AudioChunk, AudioStart, AudioStop
    from wyoming.asr import Transcript
    from wyoming.event import Event
    from wyoming.pipeline import PipelineStage, RunPipeline
    from wyoming.tts import Synthesize
    WYOMING_AVAILABLE = True
except ImportError:
    WYOMING_AVAILABLE = False


logger = logging.getLogger(__name__)


class WyomingClient:
    """TCP client for Wyoming protocol communication."""

    def __init__(self, uri: str):
        """Initialize Wyoming client.

        Args:
            uri: Wyoming endpoint URI (tcp://host:port)
        """
        if not WYOMING_AVAILABLE:
            raise ImportError("wyoming package is required. Install with: pip install wyoming")

        self.uri = uri
        self.socket: Optional[socket.socket] = None
        self.connected = False

        # Parse URI
        parsed = urlparse(uri)
        if parsed.scheme != "tcp":
            raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")

        self.host = parsed.hostname
        self.port = parsed.port

        if not self.host or not self.port:
            raise ValueError(f"Invalid URI format: {uri}")

    def connect(self) -> None:
        """Establish TCP connection to Wyoming endpoint."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to {self.host}:{self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

    def disconnect(self) -> None:
        """Close TCP connection."""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass  # Ignore errors during cleanup
            self.socket = None
            self.connected = False
            logger.info("Disconnected")

    def send_event(self, event) -> None:
        """Send Wyoming event to server.

        Args:
            event: Wyoming event object (AudioStart, etc.)
        """
        if not self.connected or not self.socket:
            raise ConnectionError("Not connected")

        try:
            import json

            # Get the actual Event object
            actual_event = event.event()
            event_dict = actual_event.to_dict()

            # Add payload length if present (Wyoming protocol requirement)
            if actual_event.payload:
                event_dict['payload_length'] = len(actual_event.payload)

            # Serialize as JSON line (Wyoming protocol format)
            json_line = json.dumps(event_dict, ensure_ascii=False)
            self.socket.sendall((json_line + '\n').encode('utf-8'))

            # Send payload if present
            if actual_event.payload:
                self.socket.sendall(actual_event.payload)

            logger.debug(f"Sent event: {type(event).__name__}")
        except Exception as e:
            raise ConnectionError(f"Failed to send event: {e}")

    def send_audio_chunk(self, audio_bytes: bytes) -> None:
        """Send raw audio bytes.

        Args:
            audio_bytes: Raw PCM audio data
        """
        if not self.connected or not self.socket:
            raise ConnectionError("Not connected")

        try:
            self.socket.sendall(audio_bytes)
            logger.debug(f"Sent {len(audio_bytes)} bytes of audio")
        except Exception as e:
            raise ConnectionError(f"Failed to send audio chunk: {e}")

    def receive_event(self, timeout: float = 30.0) -> Optional[Event]:
        """Receive and parse next Wyoming event from server.

        Args:
            timeout: Maximum time to wait for event in seconds

        Returns:
            Wyoming Event object or None if timeout/connection closed
        """
        if not self.connected or not self.socket:
            raise ConnectionError("Not connected")

        # Set socket timeout
        original_timeout = self.socket.gettimeout()
        self.socket.settimeout(timeout)

        try:
            import json

            # Read line by line until we get a complete event
            buffer = b""
            while True:
                chunk = self.socket.recv(1024)
                if not chunk:
                    # Connection closed
                    return None

                buffer += chunk

                # Look for newline
                newline_pos = buffer.find(b'\n')
                if newline_pos >= 0:
                    # Extract complete line
                    line = buffer[:newline_pos]
                    buffer = buffer[newline_pos + 1:]

                    # Parse Wyoming event
                    try:
                        event_dict = json.loads(line.decode('utf-8'))

                        # Check for payload
                        payload = None
                        payload_length = event_dict.get('payload_length')
                        if payload_length and payload_length > 0:
                            # Read payload bytes
                            payload_bytes = b""
                            while len(payload_bytes) < payload_length:
                                remaining = payload_length - len(payload_bytes)
                                chunk = self.socket.recv(min(remaining, 4096))
                                if not chunk:
                                    raise ConnectionError("Connection closed while reading payload")
                                payload_bytes += chunk
                            payload = payload_bytes

                        # Create Event
                        event = Event.from_dict(event_dict)
                        if payload:
                            event = Event(type=event.type, data=event.data, payload=payload)

                        logger.debug(f"Received event: {event.type}")
                        return event
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse Wyoming event JSON: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to parse Wyoming event: {e}")
                        continue

        except socket.timeout:
            logger.debug("Receive timeout")
            return None
        except Exception as e:
            raise ConnectionError(f"Failed to receive event: {e}")
        finally:
            # Restore original timeout
            self.socket.settimeout(original_timeout)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()