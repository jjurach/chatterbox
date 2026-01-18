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
from wyoming.server import AsyncServer
from wyoming.tts import Synthesize, SynthesizeVoice

from cackle.agent import VoiceAssistantAgent
from cackle.services import WhisperSTTService, PiperTTSService

logger = logging.getLogger(__name__)


class VoiceAssistantServer(AsyncServer):
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
        host: str | None = None,
        port: int | None = None,
        ollama_base_url: str = "http://localhost:11434/v1",
        ollama_model: str = "llama3.1:8b",
        ollama_temperature: float = 0.7,
        conversation_window_size: int = 3,
        debug: bool = False,
        mode: str = "full",
        stt_model: str = "base",
        stt_device: str = "cpu",
        tts_voice: str = "en_US-lessac-medium",
    ):
        """Initialize the Wyoming voice assistant server.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 10700)
            ollama_base_url: Base URL for Ollama's OpenAI-compatible API
            ollama_model: The Ollama model to use
            ollama_temperature: Model temperature for response generation
            conversation_window_size: Number of messages to keep in memory
            debug: Enable debug mode with enhanced Wyoming event logging
            mode: Server mode - 'full' (VA), 'stt_only', 'tts_only', or 'combined'
            stt_model: Whisper model size (tiny, base, small, medium, large)
            stt_device: Device for STT (cpu, cuda)
            tts_voice: Piper voice name
        """
        super().__init__()

        # Server settings
        self.host = host or "0.0.0.0"
        self.port = port or 10700
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
            )

        if mode in ("tts_only", "combined", "full"):
            self.tts_service = PiperTTSService(voice=tts_voice)

        logger.info(f"Server initialized on {self.host}:{self.port} (mode: {mode})")
        if debug:
            logger.info("Server debug mode enabled")

    async def handle_event(self, event: Event) -> Optional[Event]:
        """Handle incoming Wyoming protocol events.

        This method is called for each event received from a connected client.
        It routes events to appropriate handlers based on their type.

        Args:
            event: The incoming event from the ESP32 device

        Returns:
            An optional response event to send back to the client
        """
        timestamp = datetime.now().isoformat()
        event_type = type(event).__name__

        # Audio stream events
        if isinstance(event, AudioStart):
            logger.debug("Audio stream started")
            if self.debug:
                logger.info(f"[{timestamp}] [WYOMING] AudioStart event received")
            self.audio_buffer.clear()
            return None

        if isinstance(event, AudioChunk):
            logger.debug(f"Received audio chunk: {len(event.audio)} bytes")
            if self.debug:
                logger.debug(
                    f"[{timestamp}] [WYOMING] AudioChunk: {len(event.audio)} bytes"
                )
            # Buffer audio for STT processing
            self.audio_buffer.extend(event.audio)
            return None

        if isinstance(event, AudioStop):
            logger.debug("Audio stream stopped")
            if self.debug:
                logger.info(f"[{timestamp}] [WYOMING] AudioStop event received")
            return None

        # Speech recognition events
        if isinstance(event, Transcribe):
            logger.debug("Transcription requested")
            if self.debug:
                logger.info(f"[{timestamp}] [WYOMING] Transcribe event received")
            return await self._handle_transcribe(event)

        if isinstance(event, Transcript):
            logger.info(f"Received transcript: {event.text}")
            if self.debug:
                logger.info(
                    f"[{timestamp}] [WYOMING] Transcript received: {event.text}"
                )
            return await self._process_transcript(event)

        logger.debug(f"Unhandled event type: {event_type}")
        if self.debug:
            logger.debug(f"[{timestamp}] [WYOMING] Unhandled event: {event_type}")
        return None

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
                return Transcript(text="", confidence=0.0)

            # Transcribe the buffered audio
            result = await self.stt_service.transcribe(bytes(self.audio_buffer))
            self.audio_buffer.clear()

            return Transcript(
                text=result["text"],
                confidence=result.get("confidence", 0.0),
            )

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return Transcript(text="", confidence=0.0)

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

    async def run(self) -> None:
        """Start the Wyoming server and listen for incoming connections.

        This method validates dependencies before starting the server
        to provide early error detection.

        Raises:
            RuntimeError: If required services are not accessible
        """
        # Validate dependencies based on mode
        if self.mode in ("full", "combined"):
            if not await self._validate_ollama_connection():
                raise RuntimeError(
                    "Ollama is not accessible. Please start it first with: ollama serve"
                )

        # Load STT/TTS models if needed
        if self.stt_service:
            logger.info("Preloading STT model (this may take a moment)...")
            await self.stt_service.load_model()

        if self.tts_service:
            logger.info("Preloading TTS voice (this may take a moment)...")
            await self.tts_service.load_voice()

        # Create server from URI and set up handler
        uri = f"tcp://{self.host}:{self.port}"
        logger.info(f"Starting Wyoming server on {uri}")

        server = AsyncServer.from_uri(uri)

        # Start the server with event handler
        await server.start(self.handle_event)
