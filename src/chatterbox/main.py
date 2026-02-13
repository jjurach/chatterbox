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

from langchain_core import globals as langchain_globals

from chatterbox.config import get_settings
from chatterbox.adapters.wyoming import WyomingServer

# Load configuration
settings = get_settings()

# Configure logging based on settings
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_rest_server(debug: bool = False) -> None:
    """Run the REST API server.

    Args:
        debug: Enable debug mode
    """
    from chatterbox.adapters.rest import create_app
    import uvicorn

    app = create_app(
        mode=settings.server_mode,
        stt_model=settings.stt_model,
        stt_device=settings.stt_device,
        tts_voice=settings.tts_voice,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        ollama_temperature=settings.ollama_temperature,
        conversation_window_size=settings.conversation_window_size,
    )

    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.rest_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main(debug: bool = False) -> None:
    """Main entry point for the voice assistant.

    Handles:
    1. Loading configuration
    2. Creating the server instance(s)
    3. Registering signal handlers for graceful shutdown
    4. Running the server(s) until interrupted

    Args:
        debug: Enable debug mode with detailed LangChain logging
    """
    # Enable LangChain debugging if requested
    if debug:
        langchain_globals.set_debug(True)
        logger.info("LangChain debug mode enabled")

    # Create Wyoming server with configuration
    server = WyomingServer(
        host=settings.host,
        port=settings.port,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        ollama_temperature=settings.ollama_temperature,
        conversation_window_size=settings.conversation_window_size,
        debug=debug,
        mode=settings.server_mode,
        stt_model=settings.stt_model,
        stt_device=settings.stt_device,
        tts_voice=settings.tts_voice,
        whisper_cache_dir=settings.whisper_cache_dir,
        piper_cache_dir=settings.piper_cache_dir,
    )

    # Set up graceful shutdown
    shutdown_event = asyncio.Event()
    tasks = []
    loop = asyncio.get_running_loop()

    def signal_handler() -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers for common shutdown signals
    # Use loop.add_signal_handler() for proper asyncio integration
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    try:
        # Wyoming server
        logger.info(
            f"Starting Wyoming server in {settings.server_mode} mode "
            f"on {settings.host}:{settings.port}"
        )
        wyoming_task = asyncio.create_task(server.run())
        tasks.append(wyoming_task)

        # REST API server (optional)
        if settings.enable_rest:
            logger.info(
                f"Starting REST API server on {settings.host}:{settings.rest_port}"
            )
            rest_task = asyncio.create_task(run_rest_server(debug=debug))
            tasks.append(rest_task)

        # Wait for shutdown event
        await shutdown_event.wait()
        logger.info("Shutdown event received, cancelling all tasks...")

        # Graceful shutdown - cancel all tasks
        for task in tasks:
            if not task.done():
                logger.info(f"Cancelling task: {task.get_name()}")
                task.cancel()

        # Wait for all tasks to complete (with timeout)
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning("Server shutdown timeout - forcing termination")
            # Force cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

        logger.info("Server shutdown complete")

    except asyncio.CancelledError:
        logger.info("Server shutdown complete")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


def cli_main() -> None:
    """Entry point for the chatterbox-server console script."""
    parser = argparse.ArgumentParser(
        description="Wyoming Voice Assistant Server with STT/TTS"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed LangChain logging",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "stt_only", "tts_only", "combined"],
        default=settings.server_mode,
        help="Server mode (default: full)",
    )
    parser.add_argument(
        "--rest",
        action="store_true",
        help="Enable REST API server",
    )
    parser.add_argument(
        "--rest-port",
        type=int,
        default=settings.rest_port,
        help="REST API server port (default: 8080)",
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="small.en",
        help="Whisper model size (tiny, base, small, medium, large; default: small.en)",
    )
    parser.add_argument(
        "--piper-voice",
        type=str,
        default="en_US-danny-low",
        help="Piper voice name (default: en_US-danny-low)",
    )
    parser.add_argument(
        "--whisper-cache-dir",
        type=str,
        default=None,
        help="Cache directory for Whisper models (default: ~/.cache/chatterbox/whisper)",
    )
    parser.add_argument(
        "--piper-cache-dir",
        type=str,
        default=None,
        help="Cache directory for Piper voices (default: ~/.cache/chatterbox/piper)",
    )
    args = parser.parse_args()

    # Override settings with CLI arguments if provided
    if args.mode != settings.server_mode:
        settings.server_mode = args.mode

    if args.rest:
        settings.enable_rest = True

    if args.rest_port != settings.rest_port:
        settings.rest_port = args.rest_port

    # Override model settings
    if args.whisper_model != "small.en":
        settings.stt_model = args.whisper_model

    if args.piper_voice != "en_US-danny-low":
        settings.tts_voice = args.piper_voice

    # Store cache directories in settings for later use
    if args.whisper_cache_dir:
        settings.whisper_cache_dir = args.whisper_cache_dir

    if args.piper_cache_dir:
        settings.piper_cache_dir = args.piper_cache_dir

    asyncio.run(main(debug=args.debug))


if __name__ == "__main__":
    cli_main()