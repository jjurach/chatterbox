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
import os
import pathlib
import signal
import sys
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


async def main(debug: bool = False, verbose: bool = False) -> None:
    """Main entry point for the voice assistant.

    Handles:
    1. Loading configuration
    2. Creating the server instance(s)
    3. Registering signal handlers for graceful shutdown
    4. Running the server(s) until interrupted

    Args:
        debug: Enable debug mode with detailed LangChain logging
        verbose: Enable verbose logging for protocol messages and service details
    """
    # Enable LangChain debugging if requested
    if debug:
        langchain_globals.set_debug(True)
        logger.info("LangChain debug mode enabled")

    if verbose:
        logger.info("Verbose logging enabled")

    # Create Wyoming server with configuration
    server = WyomingServer(
        host=settings.host,
        port=settings.port,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        ollama_temperature=settings.ollama_temperature,
        conversation_window_size=settings.conversation_window_size,
        debug=debug,
        verbose=verbose,
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


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to serve and start subcommands."""
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed LangChain logging",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (Wyoming protocol messages, STT/TTS details, LLM interactions)",
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


def apply_cli_settings(args: argparse.Namespace) -> None:
    """Apply CLI arguments to settings."""
    if args.mode != settings.server_mode:
        settings.server_mode = args.mode

    if args.rest:
        settings.enable_rest = True

    if args.rest_port != settings.rest_port:
        settings.rest_port = args.rest_port

    if args.whisper_model != "small.en":
        settings.stt_model = args.whisper_model

    if args.piper_voice != "en_US-danny-low":
        settings.tts_voice = args.piper_voice

    if args.whisper_cache_dir:
        settings.whisper_cache_dir = args.whisper_cache_dir

    if args.piper_cache_dir:
        settings.piper_cache_dir = args.piper_cache_dir


def cmd_serve(args: argparse.Namespace) -> None:
    """Run chatterbox in foreground (serve subcommand)."""
    apply_cli_settings(args)
    asyncio.run(main(debug=args.debug, verbose=args.verbose))


def cmd_start(args: argparse.Namespace) -> None:
    """Start chatterbox as a background daemon (start subcommand)."""
    apply_cli_settings(args)

    # Determine log and pid file paths
    log_dir = pathlib.Path(args.log_file).parent if args.log_file else pathlib.Path("logs")
    pid_file = pathlib.Path(args.pid_file) if args.pid_file else log_dir / "chatterbox.pid"
    log_file = pathlib.Path(args.log_file) if args.log_file else log_dir / "chatterbox.log"

    # Create logs directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Fork to background
    pid = os.fork()
    if pid > 0:
        # Parent process: print PID and exit
        logger.info(f"Started chatterbox daemon with PID {pid}")
        print(f"Chatterbox started with PID {pid}")
        print(f"Log file: {log_file}")
        print(f"PID file: {pid_file}")
        return

    # Child process continues
    os.setsid()  # Create new session
    os.umask(0)

    # Redirect output to log file
    with open(log_file, "a") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

    # Write PID file
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        asyncio.run(main(debug=args.debug, verbose=args.verbose))
    finally:
        # Clean up PID file on exit
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop the background chatterbox daemon (stop subcommand)."""
    pid_file = pathlib.Path(args.pid_file) if args.pid_file else pathlib.Path("logs/chatterbox.pid")

    if not pid_file.exists():
        logger.error(f"PID file not found: {pid_file}")
        print(f"Error: PID file not found: {pid_file}")
        sys.exit(1)

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        os.kill(pid, signal.SIGTERM)
        logger.info(f"Sent SIGTERM to process {pid}")
        print(f"Sent SIGTERM to chatterbox (PID {pid})")
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Error reading PID file: {e}")
        print(f"Error reading PID file: {e}")
        sys.exit(1)
    except ProcessLookupError:
        logger.error(f"Process {pid} not found")
        print(f"Error: Process {pid} not found")
        sys.exit(1)


def cli_main() -> None:
    """Entry point for the chatterbox console script with subcommands."""
    parser = argparse.ArgumentParser(
        description="Wyoming Voice Assistant Server with STT/TTS"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # serve subcommand
    serve_parser = subparsers.add_parser(
        "serve",
        help="Run chatterbox in foreground"
    )
    add_common_args(serve_parser)
    serve_parser.set_defaults(func=cmd_serve)

    # start subcommand
    start_parser = subparsers.add_parser(
        "start",
        help="Start chatterbox as a background daemon"
    )
    add_common_args(start_parser)
    start_parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log file path (default: ./logs/chatterbox.log)",
    )
    start_parser.add_argument(
        "--pid-file",
        type=str,
        default=None,
        help="PID file path (default: ./logs/chatterbox.pid)",
    )
    start_parser.set_defaults(func=cmd_start)

    # stop subcommand
    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop the background chatterbox daemon"
    )
    stop_parser.add_argument(
        "--pid-file",
        type=str,
        default=None,
        help="PID file path (default: ./logs/chatterbox.pid)",
    )
    stop_parser.set_defaults(func=cmd_stop)

    args = parser.parse_args()

    # If no command is provided, default to serve
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    cli_main()