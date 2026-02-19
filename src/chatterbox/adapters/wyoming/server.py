"""
Wyoming Voice Assistant Server.

This module implements the Wyoming protocol server that handles communication
with ESP32 devices and processes audio/text events.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from wyoming.asr import Transcript, Transcribe
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.server import AsyncServer, AsyncEventHandler
from wyoming.tts import Synthesize, SynthesizeVoice

from chatterbox.agent import VoiceAssistantAgent
from chatterbox.services import WhisperSTTService, PiperTTSService

logger = logging.getLogger(__name__)


class VoiceAssistantServer(AsyncEventHandler):
    """Wyoming protocol server for the voice assistant.

    This server handles incoming connections from ESP32 devices, processes
    audio/text events, and returns responses via the Wyoming protocol.

    Attributes:
        host: Server host address
        port: Server port number
        agent: The voice assistant agent
        ollama_base_url: URL for Ollama LLM service
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        ollama_base_url: str = "http://localhost:11434/v1",
        ollama_model: str = "llama3.1:8b",
        ollama_temperature: float = 0.7,
        conversation_window_size: int = 3,
        debug: bool = False,
        mode: str = "full",
        stt_model: str = "base",
        stt_device: str = "cpu",
        tts_voice: str = "en_US-lessac-medium",
        whisper_cache_dir: Optional[str] = None,
        piper_cache_dir: Optional[str] = None,
    ):
        """Initialize the Wyoming voice assistant server handler.

        Args:
            reader: Stream reader for the connection
            writer: Stream writer for the connection
            ollama_base_url: Base URL for Ollama's OpenAI-compatible API
            ollama_model: The Ollama model to use
            ollama_temperature: Model temperature for response generation
            conversation_window_size: Number of messages to keep in memory
            debug: Enable debug mode with enhanced Wyoming event logging
            mode: Server mode - 'full' (VA), 'stt_only', 'tts_only', or 'combined'
            stt_model: Whisper model size (tiny, base, small, medium, large)
            stt_device: Device for STT (cpu, cuda)
            tts_voice: Piper voice name
            whisper_cache_dir: Cache directory for Whisper models
            piper_cache_dir: Cache directory for Piper voices
        """
        super().__init__(reader, writer)

        # Server settings
        self.ollama_base_url = ollama_base_url
        self.debug = debug
        self.mode = mode

        # Audio buffer for STT
        self.audio_buffer = bytearray()

        # Initialize services based on mode
        self.agent: Optional[VoiceAssistantAgent] = None
        self.stt_service: Optional[WhisperSTTService] = None
        self.tts_service: Optional[PiperTTSService] = None

        if mode in ("full", "combined"):
            self.agent = VoiceAssistantAgent(
                ollama_base_url=ollama_base_url,
                ollama_model=ollama_model,
                ollama_temperature=ollama_temperature,
                conversation_window_size=conversation_window_size,
                debug=debug,
            )

        if mode in ("stt_only", "combined"):
            self.stt_service = WhisperSTTService(
                model_size=stt_model,
                device=stt_device,
                cache_dir=whisper_cache_dir,
            )

        if mode in ("tts_only", "combined", "full"):
            self.tts_service = PiperTTSService(
                voice=tts_voice,
                cache_dir=piper_cache_dir,
            )

        logger.info(f"Connection handler initialized (mode: {mode})")
        if debug:
            logger.info("Debug mode enabled")

    async def handle_event(self, event: Event) -> bool:
        """Handle incoming Wyoming protocol events.

        This method is called for each event received from a connected client.
        It routes events to appropriate handlers based on their type.

        Args:
            event: The incoming event from the ESP32 device

        Returns:
            True to continue the connection, False to disconnect
        """
        timestamp = datetime.now().isoformat()
        event_type = type(event).__name__
        event_attr_type = getattr(event, 'type', 'N/A')

        # Debug: Log detailed event information
        logger.debug(f"handle_event: type={event_type}, event.type={event_attr_type}")
        if self.debug:
            logger.info(f"[{timestamp}] [EVENT] type={event_type}, event.type={event_attr_type}, event.data={getattr(event, 'data', 'N/A')}")

        # Handle both specific event types (AudioStart, AudioChunk, etc.) and generic Event objects with type attributes
        # Wyoming library sometimes deserializes as generic Event objects

        # Audio stream events - handle both specific types and generic Events
        if isinstance(event, AudioStart) or (hasattr(event, 'type') and event.type == "audio-start"):
            logger.debug("Audio stream started")
            if self.debug:
                logger.info(f"[{timestamp}] [WYOMING] AudioStart event received")
            self.audio_buffer.clear()
            return True

        if isinstance(event, AudioChunk) or (hasattr(event, 'type') and event.type == "audio-chunk"):
            # Get audio bytes from either AudioChunk.audio or event.payload
            audio_bytes = None
            if isinstance(event, AudioChunk):
                audio_bytes = event.audio
            elif hasattr(event, 'payload') and event.payload:
                audio_bytes = event.payload

            if audio_bytes:
                logger.info(f"Buffering audio chunk: {len(audio_bytes)} bytes (total: {len(self.audio_buffer) + len(audio_bytes)} bytes)")
                if self.debug:
                    logger.debug(
                        f"[{timestamp}] [WYOMING] AudioChunk: {len(audio_bytes)} bytes"
                    )
                # Buffer audio for STT processing
                self.audio_buffer.extend(audio_bytes)
            else:
                logger.debug(f"Audio chunk received but no payload (payload={hasattr(event, 'payload')}, data={getattr(event, 'data', None)})")
            return True

        if isinstance(event, AudioStop) or (hasattr(event, 'type') and event.type == "audio-stop"):
            logger.info(f"Audio stream stopped. Total audio buffered: {len(self.audio_buffer)} bytes")
            if self.debug:
                logger.info(f"[{timestamp}] [WYOMING] AudioStop event received")

            # Auto-transcribe in satellite mode (full)
            if self.mode == "full":
                logger.info(f"Starting auto-transcription in full mode ({len(self.audio_buffer)} bytes)")
                if self.debug:
                    logger.info(f"[{timestamp}] [WYOMING] Auto-transcribe triggered")

                try:
                    response_event = await self._handle_transcribe(Transcribe())
                    if response_event:
                        logger.info(f"Transcription result: {response_event.text if hasattr(response_event, 'text') else 'N/A'}")
                        # Convert Transcript wrapper to Event for transmission
                        event_to_send = response_event.event()
                        await self.write_event(event_to_send)
                except Exception as e:
                    logger.error(f"Error in auto-transcription: {e}", exc_info=True)
                finally:
                    self.audio_buffer.clear()
            elif self.mode == "stt_only":
                # In stt_only mode, auto-transcribe when audio stops
                logger.info(f"Starting auto-transcription in stt_only mode ({len(self.audio_buffer)} bytes)")
                try:
                    response_event = await self._handle_transcribe(Transcribe())
                    if response_event:
                        logger.info(f"Transcription result: {response_event.text if hasattr(response_event, 'text') else 'N/A'}")
                        # Convert Transcript wrapper to Event for transmission
                        event_to_send = response_event.event()
                        await self.write_event(event_to_send)
                except Exception as e:
                    logger.error(f"Error in auto-transcription: {e}", exc_info=True)
                finally:
                    self.audio_buffer.clear()

            return True

        # Speech recognition events
        if isinstance(event, Transcribe) or (hasattr(event, 'type') and event.type == "transcribe"):
            logger.debug("Transcription requested")
            if self.debug:
                logger.info(f"[{timestamp}] [WYOMING] Transcribe event received")
            response_event = await self._handle_transcribe(Transcribe())
            if response_event:
                # Convert Transcript wrapper to Event for transmission
                event_to_send = response_event.event()
                await self.write_event(event_to_send)
            return True

        if isinstance(event, Transcript):
            logger.info(f"Received transcript: {event.text}")
            if self.debug:
                logger.info(
                    f"[{timestamp}] [WYOMING] Transcript received: {event.text}"
                )

            # In stt_only mode, just log the transcript (no agent to process it)
            if self.mode == "stt_only":
                logger.debug("Transcript received in stt_only mode (no response generated)")
                return True

            response_event = await self._process_transcript(event)
            if response_event:
                # Convert Synthesize wrapper to Event for transmission
                event_to_send = response_event.event()
                await self.write_event(event_to_send)
            return True

        # Text-to-Speech events
        if isinstance(event, Synthesize) or (hasattr(event, 'type') and event.type == "synthesize"):
            logger.debug("Synthesis requested")
            if self.debug:
                logger.info(f"[{timestamp}] [WYOMING] Synthesize event received")
            # Deserialize to Synthesize to reliably access .text (generic Event
            # stores text in event.data, not as a direct attribute).
            try:
                synth_event = Synthesize.from_event(event) if not isinstance(event, Synthesize) else event
                text = synth_event.text or ''
            except Exception:
                text = (event.data or {}).get('text', '') if hasattr(event, 'data') else ''
            if text:
                await self._handle_synthesize(text)
            return True

        # Handle unknown event types
        logger.debug(f"Unhandled event type: {event_type} (event.type={event_attr_type})")

        logger.debug(f"Unhandled event type: {event_type}")
        if self.debug:
            logger.debug(f"[{timestamp}] [WYOMING] Unhandled event: {event_type}")
        return True

    async def _handle_transcribe(self, event: Transcribe) -> Optional[Event]:
        """Handle Transcribe event by running STT on buffered audio.

        Args:
            event: The Transcribe event

        Returns:
            A Transcript event with transcribed text
        """
        if not self.stt_service:
            logger.error("STT service not available in this mode")
            return None

        try:
            if not self.audio_buffer:
                logger.warning("No audio data to transcribe")
                return Transcript(text="")

            logger.info(f"Starting Whisper transcription on {len(self.audio_buffer)} bytes of audio")
            # Transcribe the buffered audio
            result = await self.stt_service.transcribe(bytes(self.audio_buffer))

            logger.info(f"Whisper transcription complete: '{result.get('text', '')}'")

            return Transcript(
                text=result["text"],
            )

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return Transcript(text="")

    async def _process_transcript(self, transcript: Transcript) -> Optional[Event]:
        """Process a transcript event and generate a response.

        Args:
            transcript: The transcript event from the device

        Returns:
            A Synthesize event with the response to speak
        """
        if not self.agent:
            logger.error("Agent not available in this mode")
            return None

        try:
            # Process through the agent
            response_text = await self.agent.process_input(transcript.text)

            # Create and return a TTS (Text-to-Speech) event
            return self._create_response(response_text)

        except Exception as e:
            logger.error(f"Error processing transcript: {e}", exc_info=True)
            error_message = f"Sorry, I encountered an error: {str(e)}"
            return self._create_response(error_message)

    def _create_response(self, text: str) -> Synthesize:
        """Create a TTS event with the given text.

        Args:
            text: The text to synthesize to speech

        Returns:
            A Synthesize event configured for the device
        """
        return Synthesize(
            text=text,
            voice=SynthesizeVoice(
                name="default",
                language="en-US",
                speaker="default",
            ),
        )

    async def _handle_synthesize(self, text: str) -> None:
        """Handle Synthesize event by streaming TTS audio to client.

        Sends a sequence of Wyoming events:
        1. AudioStart with metadata (rate, width, channels)
        2. One or more AudioChunk events with PCM audio data
        3. AudioStop to signal completion

        Args:
            text: The text to synthesize to speech
        """
        if not self.tts_service:
            logger.error("TTS service not available in this mode")
            return

        try:
            logger.info(f"Starting Piper TTS synthesis: '{text}'")
            # Generate audio from text
            audio_bytes = await self.tts_service.synthesize(text)

            if not audio_bytes:
                logger.warning("TTS returned empty audio")
                return

            logger.info(f"Piper TTS synthesis complete: {len(audio_bytes)} bytes")

            # Send AudioStart with metadata
            # Piper generates 22050 Hz, 16-bit (2 bytes) mono audio
            audio_start = AudioStart(
                rate=22050,
                width=2,
                channels=1,
            )
            await self.write_event(audio_start.event())
            logger.debug("Sent AudioStart event")

            # Send audio in chunks (optimal chunk size for network streaming)
            chunk_size = 4096
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                audio_chunk = AudioChunk(rate=22050, width=2, channels=1, audio=chunk)
                await self.write_event(audio_chunk.event())
                logger.debug(f"Sent AudioChunk: {len(chunk)} bytes ({i//chunk_size + 1} chunks)")

            # Send AudioStop to signal completion
            audio_stop = AudioStop()
            await self.write_event(audio_stop.event())
            logger.info("Sent AudioStop event - TTS stream complete")

        except Exception as e:
            logger.error(f"Error synthesizing audio: {e}", exc_info=True)

    async def _validate_ollama_connection(self) -> bool:
        """Validate that Ollama is accessible and the model is available.

        Checks connectivity to the Ollama service and verifies that the
        configured model is downloaded and available.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                # Check Ollama API endpoint
                response = await client.get(
                    f"{self.ollama_base_url.rsplit('/v1', 1)[0]}/api/tags",
                    timeout=5.0,
                )

                if response.status_code != 200:
                    logger.error(f"Ollama API returned status {response.status_code}")
                    return False

                # Check if the configured model is available
                try:
                    models_data = response.json()
                    models = models_data.get("models", [])
                    model_names = [m.get("name") for m in models]

                    if self.agent.ollama_model not in model_names:
                        logger.warning(
                            f"Model {self.agent.ollama_model} not found. "
                            f"Available models: {model_names}"
                        )
                        logger.info(
                            f"Download the model with: ollama pull {self.agent.ollama_model}"
                        )
                        return False

                    logger.info("✓ Ollama connection validated successfully")
                    return True

                except Exception as e:
                    logger.error(f"Error parsing Ollama response: {e}")
                    return False

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.info("Make sure Ollama is running: ollama serve")
            return False

    async def disconnect(self) -> None:
        """Called when client disconnects."""
        logger.debug("Client disconnected")


class WyomingServer:
    """Wyoming server that manages connections and handlers."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 10700,
        ollama_base_url: str = "http://localhost:11434/v1",
        ollama_model: str = "llama3.1:8b",
        ollama_temperature: float = 0.7,
        conversation_window_size: int = 3,
        debug: bool = False,
        mode: str = "full",
        stt_model: str = "base",
        stt_device: str = "cpu",
        tts_voice: str = "en_US-lessac-medium",
        whisper_cache_dir: Optional[str] = None,
        piper_cache_dir: Optional[str] = None,
    ):
        """Initialize the Wyoming server.

        Args:
            host: Host to bind to
            port: Port to bind to
            ollama_base_url: Base URL for Ollama's OpenAI-compatible API
            ollama_model: The Ollama model to use
            ollama_temperature: Model temperature for response generation
            conversation_window_size: Number of messages to keep in memory
            debug: Enable debug mode with enhanced Wyoming event logging
            mode: Server mode - 'full' (VA), 'stt_only', 'tts_only', or 'combined'
            stt_model: Whisper model size (tiny, base, small, medium, large)
            stt_device: Device for STT (cpu, cuda)
            tts_voice: Piper voice name
            whisper_cache_dir: Cache directory for Whisper models
            piper_cache_dir: Cache directory for Piper voices
        """
        self.host = host
        self.port = port
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.ollama_temperature = ollama_temperature
        self.conversation_window_size = conversation_window_size
        self.debug = debug
        self.mode = mode
        self.stt_model = stt_model
        self.stt_device = stt_device
        self.tts_voice = tts_voice
        self.whisper_cache_dir = whisper_cache_dir
        self.piper_cache_dir = piper_cache_dir

    def handler_factory(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> VoiceAssistantServer:
        """Create a new handler for each connection."""
        return VoiceAssistantServer(
            reader=reader,
            writer=writer,
            ollama_base_url=self.ollama_base_url,
            ollama_model=self.ollama_model,
            ollama_temperature=self.ollama_temperature,
            conversation_window_size=self.conversation_window_size,
            debug=self.debug,
            mode=self.mode,
            stt_model=self.stt_model,
            stt_device=self.stt_device,
            tts_voice=self.tts_voice,
            whisper_cache_dir=self.whisper_cache_dir,
            piper_cache_dir=self.piper_cache_dir,
        )

    async def _validate_ollama_connection(self) -> bool:
        """Validate that Ollama is accessible and the model is available.

        Checks connectivity to the Ollama service and verifies that the
        configured model is downloaded and available.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                # Check Ollama API endpoint
                response = await client.get(
                    f"{self.ollama_base_url.rsplit('/v1', 1)[0]}/api/tags",
                    timeout=5.0,
                )

                if response.status_code != 200:
                    logger.error(f"Ollama API returned status {response.status_code}")
                    return False

                # Check if the configured model is available
                try:
                    models_data = response.json()
                    models = models_data.get("models", [])
                    model_names = [m.get("name") for m in models]

                    if self.ollama_model not in model_names:
                        logger.warning(
                            f"Model {self.ollama_model} not found. "
                            f"Available models: {model_names}"
                        )
                        logger.info(
                            f"Download the model with: ollama pull {self.ollama_model}"
                        )
                        return False

                    logger.info("✓ Ollama connection validated successfully")
                    return True

                except Exception as e:
                    logger.error(f"Error parsing Ollama response: {e}")
                    return False

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.info("Make sure Ollama is running: ollama serve")
            return False

    async def run(self) -> None:
        """Start the Wyoming server and listen for incoming connections.

        This method validates dependencies and pre-loads models before
        starting the server to provide early error detection and fast response times.

        Raises:
            RuntimeError: If required services are not accessible
        """
        import time

        # Validate dependencies based on mode
        if self.mode in ("full", "combined"):
            if not await self._validate_ollama_connection():
                raise RuntimeError(
                    "Ollama is not accessible. Please start it first with: ollama serve"
                )

        # Pre-load STT/TTS models before accepting connections
        if self.mode in ("stt_only", "combined"):
            logger.info(f"Initializing STT model: {self.stt_model}...")
            start_time = time.time()
            try:
                stt_service = WhisperSTTService(
                    model_size=self.stt_model,
                    device=self.stt_device,
                    cache_dir=self.whisper_cache_dir,
                )
                await stt_service.load_model()
                elapsed = time.time() - start_time
                logger.info(f"STT model loaded successfully in {elapsed:.1f}s")
            except Exception as e:
                logger.error(f"Failed to load STT model: {e}", exc_info=True)
                raise RuntimeError(f"Cannot start server: STT model failed to load - {e}")

        if self.mode in ("tts_only", "combined", "full"):
            logger.info(f"Initializing TTS voice: {self.tts_voice}...")
            start_time = time.time()
            try:
                tts_service = PiperTTSService(
                    voice=self.tts_voice,
                    cache_dir=self.piper_cache_dir,
                )
                await tts_service.load_voice()
                elapsed = time.time() - start_time
                logger.info(f"TTS voice loaded successfully in {elapsed:.1f}s")
            except Exception as e:
                logger.error(f"Failed to load TTS voice: {e}", exc_info=True)
                raise RuntimeError(f"Cannot start server: TTS voice failed to load - {e}")

        # Create server from URI and set up handler
        uri = f"tcp://{self.host}:{self.port}"
        logger.info(f"Starting Wyoming server on {uri} (mode: {self.mode})")

        try:
            server = AsyncServer.from_uri(uri)
            logger.info(f"Wyoming AsyncServer created successfully from URI: {uri}")
        except Exception as e:
            logger.error(f"Failed to create Wyoming server from URI {uri}: {e}", exc_info=True)
            raise

        # Start the server with handler factory
        # Use run() instead of start() to block and serve forever
        try:
            logger.info(f"All models loaded. Server is ready to accept connections...")
            await server.run(self.handler_factory)
            logger.info("AsyncServer.run() completed (server shutting down)")
        except Exception as e:
            logger.error(f"Failed to run Wyoming server: {e}", exc_info=True)
            raise