"""
Wyoming Voice Assistant - Main Entry Point.

This module is the entry point for the voice assistant server. It handles
initialization, configuration loading, graceful shutdown, and orchestrates
the server startup.

Architecture:
    - config.py: Configuration management
    - tools.py: Agent tools definition
    - agent.py: LangChain agent management
    - server.py: Wyoming protocol server
    - main.py: Orchestration and entry point
"""

import argparse
import asyncio
import logging
import signal
from typing import Any

from langchain import globals as langchain_globals

from backend.src.config import get_settings
from backend.src.server import VoiceAssistantServer

# Load configuration
settings = get_settings()

# Configure logging based on settings
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(debug: bool = False) -> None:
    """Main entry point for the voice assistant.

    Handles:
    1. Loading configuration
    2. Creating the server instance
    3. Registering signal handlers for graceful shutdown
    4. Running the server until interrupted

    Args:
        debug: Enable debug mode with detailed LangChain logging
    """
    # Enable LangChain debugging if requested
    if debug:
        langchain_globals.set_debug(True)
        logger.info("LangChain debug mode enabled")

    # Create server with configuration
    server = VoiceAssistantServer(
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
        """Handle shutdown signals gracefully.

        Args:
            sig: Signal number
            frame: Stack frame (unused)
        """
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers for common shutdown signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run server until shutdown signal
        server_task = asyncio.create_task(server.run())

        # Wait for shutdown event
        await shutdown_event.wait()

        # Graceful shutdown
        logger.info("Shutting down server...")
        server_task.cancel()

        try:
            await server_task
        except asyncio.CancelledError:
            logger.info("Server shutdown complete")

    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wyoming Voice Assistant Server"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed LangChain logging",
    )
    args = parser.parse_args()

    asyncio.run(main(debug=args.debug))
