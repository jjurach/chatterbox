"""Wyoming Voice Assistant Client (Home Assistant Emulator).

This module provides a command-line tool to test the Wyoming voice assistant
backend by emulating Home Assistant behavior and sending Wyoming protocol events.

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
import wave
from pathlib import Path
from typing import Optional

from wyoming.asr import Transcript, Transcribe
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.event import Event, async_read_event, async_write_event
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
    # Use Wyoming's built-in serialization
    await async_write_event(event, writer)


async def read_event(reader: asyncio.StreamReader) -> Optional[Event]:
    """Read a Wyoming event from the server.

    Args:
        reader: StreamReader for the connection

    Returns:
        The received event, or None if connection closed
    """
    try:
        # Use Wyoming's built-in deserialization with timeout
        event = await asyncio.wait_for(
            async_read_event(reader), timeout=30.0
        )
        return event

    except asyncio.TimeoutError:
        logger.error("Timeout waiting for response from server")
        return None
    except Exception as e:
        logger.error(f"Error reading event: {e}")
        return None


async def test_stt(
    audio_file: str,
    host: str = "localhost",
    port: int = 10700,
    timeout: float = 20.0,
) -> None:
    """Test STT pipeline end-to-end.

    Emulates Home Assistant behavior by sending:
    1. Transcribe event
    2. AudioStart event
    3. AudioChunk events (from WAV file)
    4. AudioStop event
    5. Waits for Transcript response

    Args:
        audio_file: Path to WAV audio file to transcribe
        host: Server host (default: localhost)
        port: Server port (default: 10700)
        timeout: Timeout in seconds for response (default: 20.0)
    """
    try:
        # Verify audio file exists
        if not Path(audio_file).exists():
            logger.error(f"Audio file not found: {audio_file}")
            return

        # Connect to server
        logger.info(f"Connecting to {host}:{port}...")
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5.0
        )
        logger.info("Connected to server")

        try:
            # Send Transcribe event
            logger.info("Sending Transcribe event...")
            transcribe_event = Transcribe()
            await async_write_event(transcribe_event, writer)

            # Send AudioStart event
            logger.info("Sending AudioStart event...")
            audio_start = AudioStart(rate=16000, width=2, channels=1)
            await async_write_event(audio_start.event(), writer)

            # Read audio from WAV file and send in chunks
            logger.info(f"Reading audio from {audio_file}...")
            with wave.open(audio_file, 'rb') as wf:
                audio_data = wf.readframes(wf.getnframes())
                chunk_size = 4096
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    audio_chunk = AudioChunk(audio=chunk)
                    await async_write_event(audio_chunk.event(), writer)
                    logger.debug(f"Sent AudioChunk: {len(chunk)} bytes")

            # Send AudioStop event
            logger.info("Sending AudioStop event...")
            audio_stop = AudioStop()
            await async_write_event(audio_stop.event(), writer)

            # Wait for Transcript response
            logger.info(f"Waiting for Transcript response (timeout: {timeout}s)...")
            start_time = asyncio.get_event_loop().time()
            transcript_text = None

            while asyncio.get_event_loop().time() - start_time < timeout:
                event = await read_event(reader)
                if event is None:
                    break

                if event and event.type == "transcript":
                    if event.data and "text" in event.data:
                        transcript_text = event.data["text"]
                        logger.info(f"✓ Transcript received: {transcript_text}")
                        print(f"Transcribed text: {transcript_text}")
                        break
                else:
                    logger.debug(f"Received event: {event.type if event else 'None'}")

            if transcript_text is None:
                logger.error("✗ Timeout waiting for transcript response")
                return

        finally:
            writer.close()
            await writer.wait_closed()
            logger.info("Connection closed")

    except asyncio.TimeoutError:
        logger.error(f"Timeout connecting to {host}:{port}")
    except Exception as e:
        logger.error(f"Error in STT test: {e}", exc_info=True)


async def test_tts(
    text: str,
    output_file: Optional[str] = None,
    host: str = "localhost",
    port: int = 10700,
    timeout: float = 20.0,
) -> None:
    """Test TTS pipeline end-to-end.

    Emulates Home Assistant behavior by sending:
    1. Synthesize event with text
    2. Waits for AudioStart + AudioChunk events + AudioStop

    Args:
        text: Text to synthesize
        output_file: Optional path to save generated audio
        host: Server host (default: localhost)
        port: Server port (default: 10700)
        timeout: Timeout in seconds for response (default: 20.0)
    """
    try:
        # Connect to server
        logger.info(f"Connecting to {host}:{port}...")
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5.0
        )
        logger.info("Connected to server")

        try:
            # Send Synthesize event
            logger.info(f"Sending Synthesize event with text: {text}")
            synthesize = Synthesize(text=text)
            await async_write_event(synthesize.event(), writer)

            # Collect audio chunks
            logger.info(f"Waiting for audio stream (timeout: {timeout}s)...")
            start_time = asyncio.get_event_loop().time()
            audio_chunks = []
            audio_info = None
            stream_complete = False

            while asyncio.get_event_loop().time() - start_time < timeout:
                event = await read_event(reader)
                if event is None:
                    break

                if event:
                    if event.type == "audio-start":
                        if event.data:
                            audio_info = event.data
                            logger.info(f"AudioStart: rate={audio_info.get('rate')}, "
                                      f"width={audio_info.get('width')}, channels={audio_info.get('channels')}")
                    elif event.type == "audio-chunk":
                        if event.payload:
                            audio_chunks.append(event.payload)
                            logger.debug(f"AudioChunk: {len(event.payload)} bytes")
                    elif event.type == "audio-stop":
                        logger.info("AudioStop event received - stream complete")
                        stream_complete = True
                        break
                    else:
                        logger.debug(f"Received event: {event.type}")

            if not stream_complete:
                logger.error("✗ Timeout or incomplete stream")
                return

            if not audio_chunks:
                logger.error("✗ No audio data received")
                return

            total_audio = b''.join(audio_chunks)
            logger.info(f"✓ Received complete audio stream: {len(total_audio)} bytes")
            print(f"Synthesized audio: {len(total_audio)} bytes")

            # Optionally save to file
            if output_file:
                logger.info(f"Saving audio to {output_file}...")
                rate = audio_info.get('rate', 22050) if audio_info else 22050
                width = audio_info.get('width', 2) if audio_info else 2
                channels = audio_info.get('channels', 1) if audio_info else 1

                with wave.open(output_file, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(width)
                    wf.setframerate(rate)
                    wf.writeframes(total_audio)
                logger.info(f"✓ Audio saved to {output_file}")

        finally:
            writer.close()
            await writer.wait_closed()
            logger.info("Connection closed")

    except asyncio.TimeoutError:
        logger.error(f"Timeout connecting to {host}:{port}")
    except Exception as e:
        logger.error(f"Error in TTS test: {e}", exc_info=True)


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
            # Create Transcript and convert to Event using the event() method
            transcript = Transcript(text=text)
            event = transcript.event()
            await send_event(reader, writer, event)

            # Wait for response
            logger.info("Waiting for response...")
            while True:
                event = await read_event(reader)
                if event is None:
                    break

                # Check if it's a Synthesize event (the response)
                if event and event.type == "synthesize":
                    # Parse the event data
                    if event.data and "text" in event.data:
                        print(event.data["text"])
                        logger.info(f"Received response: {event.data['text']}")
                    break
                else:
                    logger.debug(f"Received event: {event.type if event else 'None'}")

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
    """Entry point for the Wyoming client test script."""
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
        description="Wyoming Voice Assistant Client - Test STT/TTS pipelines",
        prog="chatterbox-wyoming-client",
    )

    # Create subparsers for different test modes
    subparsers = parser.add_subparsers(dest="command", help="Test command")

    # Test transcript (legacy)
    test_parser = subparsers.add_parser("test", help="Send a test transcript")
    test_parser.add_argument("text", help="Text to send as a transcript")

    # Test STT
    stt_parser = subparsers.add_parser("stt", help="Test STT pipeline")
    stt_parser.add_argument("audio_file", help="Path to WAV audio file")
    stt_parser.add_argument("--timeout", type=float, default=20.0,
                           help="Timeout in seconds (default: 20)")

    # Test TTS
    tts_parser = subparsers.add_parser("tts", help="Test TTS pipeline")
    tts_parser.add_argument("text", help="Text to synthesize")
    tts_parser.add_argument("--output", type=str, help="Save audio to file")
    tts_parser.add_argument("--timeout", type=float, default=20.0,
                           help="Timeout in seconds (default: 20)")

    # Common options for all commands
    for subparser in [test_parser, stt_parser, tts_parser]:
        subparser.add_argument("--host", default=default_host,
                             help=f"Server host (default: {default_host})")
        subparser.add_argument("--port", type=int, default=default_port,
                             help=f"Server port (default: {default_port})")
        subparser.add_argument("--debug", action="store_true",
                             help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )

    # Default to 'test' command if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run the selected test
    if args.command == "test":
        asyncio.run(test_backend(args.text, args.host, args.port))
    elif args.command == "stt":
        asyncio.run(test_stt(args.audio_file, args.host, args.port, args.timeout))
    elif args.command == "tts":
        asyncio.run(test_tts(args.text, args.output, args.host, args.port, args.timeout))


if __name__ == "__main__":
    main()
