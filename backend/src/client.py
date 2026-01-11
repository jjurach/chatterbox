"""Client Test Harness for Chatterbox3B Backend.

This module provides a command-line tool to test the Wyoming voice assistant
backend by sending transcript events directly to the server.

Environment variables:
  CHATTERBOX_SERVER: Server address in format "host:port"
  CHATTERBOX_HOST: Server hostname (default: localhost)
  CHATTERBOX_PORT: Server port (default: 10700)
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from wyoming.asr import Transcript
from wyoming.event import Event
from wyoming.tts import Synthesize

logger = logging.getLogger(__name__)


async def send_event(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, event: Event
) -> None:
    """Send a Wyoming event to the server.

    Args:
        reader: StreamReader for the connection
        writer: StreamWriter for the connection
        event: The event to send
    """
    # Serialize the event using Wyoming's protocol
    event_bytes = event.to_bytes()
    writer.write(event_bytes)
    await writer.drain()


async def read_event(reader: asyncio.StreamReader) -> Optional[Event]:
    """Read a Wyoming event from the server.

    Args:
        reader: StreamReader for the connection

    Returns:
        The received event, or None if connection closed
    """
    try:
        # Read the event type line (ending with newline)
        line = await asyncio.wait_for(reader.readuntil(b"\n"), timeout=30.0)
        if not line:
            return None

        # Parse the event from the line
        event = Event.from_bytes(line)
        return event

    except asyncio.TimeoutError:
        logger.error("Timeout waiting for response from server")
        return None
    except Exception as e:
        logger.error(f"Error reading event: {e}")
        return None


async def test_backend(
    text: str,
    host: str = "localhost",
    port: int = 10700,
) -> None:
    """Send a test transcript to the backend server.

    Args:
        text: The text to send as a transcript
        host: Server host (default: localhost)
        port: Server port (default: 10700)
    """
    try:
        # Connect to the server
        logger.info(f"Connecting to {host}:{port}...")
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5.0
        )
        logger.info("Connected to server")

        try:
            # Send transcript event
            logger.info(f"Sending transcript: {text}")
            transcript_event = Transcript(text=text)
            await send_event(reader, writer, transcript_event)

            # Wait for response
            logger.info("Waiting for response...")
            while True:
                event = await read_event(reader)
                if event is None:
                    break

                # Check if it's a Synthesize event (the response)
                if isinstance(event, Synthesize):
                    print(event.text)
                    logger.info(f"Received response: {event.text}")
                    break
                else:
                    logger.debug(f"Received event: {type(event).__name__}")

        finally:
            writer.close()
            await writer.wait_closed()
            logger.info("Connection closed")

    except asyncio.TimeoutError:
        logger.error(f"Timeout connecting to {host}:{port}")
        sys.exit(1)
    except ConnectionRefusedError:
        logger.error(f"Connection refused by {host}:{port}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Entry point for the chatterbox-client console script."""
    # Get defaults from environment variables
    env_server = os.environ.get("CHATTERBOX_SERVER")
    default_host = "localhost"
    default_port = 10700

    if env_server:
        # Parse CHATTERBOX_SERVER in format "host:port"
        if ":" in env_server:
            parts = env_server.rsplit(":", 1)
            default_host = parts[0]
            try:
                default_port = int(parts[1])
            except ValueError:
                print(f"Error: Invalid port in CHATTERBOX_SERVER: {env_server}")
                sys.exit(1)
        else:
            default_host = env_server
    else:
        # Individual env vars override defaults
        default_host = os.environ.get("CHATTERBOX_HOST", default_host)
        default_port = int(os.environ.get("CHATTERBOX_PORT", default_port))

    parser = argparse.ArgumentParser(
        description="Test the Chatterbox3B voice assistant backend",
        prog="chatterbox3b-client",
    )
    parser.add_argument(
        "text",
        help="Text to send as a transcript to the server",
    )
    parser.add_argument(
        "--host",
        default=default_host,
        help=f"Server host (default: {default_host}, or CHATTERBOX_HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help=f"Server port (default: {default_port}, or CHATTERBOX_PORT env var)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )

    # Run the test
    asyncio.run(test_backend(args.text, args.host, args.port))


if __name__ == "__main__":
    main()
