#!/usr/bin/env python3
"""
Example: Running a Wyoming Protocol Voice Assistant Server

This example shows how to use the chatterbox-agent library with a Wyoming
protocol server for ESP32 voice devices.

Prerequisites:
    - Ollama running with llama3.1:8b model
    - ESP32-S3-BOX-3B or other Wyoming-compatible device

Usage:
    python examples/wyoming_server.py
    python examples/wyoming_server.py --debug
"""

import argparse
import asyncio
import logging
import signal
from typing import Any

from langchain_core import globals as langchain_globals
from chatterbox.config import get_settings
from chatterbox.adapters.wyoming import WyomingServer


async def main(debug: bool = False) -> None:
    """Run the Wyoming voice assistant server."""
    # Load configuration from environment
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Enable LangChain debugging if requested
    if debug:
        langchain_globals.set_debug(True)

    # Create and configure the server
    server = WyomingServer(
        host=settings.host,
        port=settings.port,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        ollama_temperature=settings.ollama_temperature,
        conversation_window_size=settings.conversation_window_size,
        debug=debug,
    )

    # Set up graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig: int, frame: Any) -> None:
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run server until interrupted
    server_task = asyncio.create_task(server.run())
    await shutdown_event.wait()

    # Graceful shutdown
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wyoming Voice Assistant Server"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    args = parser.parse_args()

    asyncio.run(main(debug=args.debug))