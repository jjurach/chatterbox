"""
Wyoming Voice Assistant Server.

This module implements the Wyoming protocol server that handles communication
with ESP32 devices and processes audio/text events.
"""

import asyncio
import logging
from typing import Optional

import httpx
from wyoming.asr import Transcript, Transcribe
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.server import AsyncServer
from wyoming.tts import Synthesize, SynthesizeVoice

from backend.src.agent import VoiceAssistantAgent

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
    ):
        """Initialize the Wyoming voice assistant server.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 10700)
            ollama_base_url: Base URL for Ollama's OpenAI-compatible API
            ollama_model: The Ollama model to use
            ollama_temperature: Model temperature for response generation
            conversation_window_size: Number of messages to keep in memory
        """
        super().__init__()

        # Server settings
        self.host = host or "0.0.0.0"
        self.port = port or 10700
        self.ollama_base_url = ollama_base_url

        # Initialize the agent
        self.agent = VoiceAssistantAgent(
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            ollama_temperature=ollama_temperature,
            conversation_window_size=conversation_window_size,
        )

        logger.info(f"Server initialized on {self.host}:{self.port}")

    async def handle_event(self, event: Event) -> Optional[Event]:
        """Handle incoming Wyoming protocol events.

        This method is called for each event received from a connected client.
        It routes events to appropriate handlers based on their type.

        Args:
            event: The incoming event from the ESP32 device

        Returns:
            An optional response event to send back to the client
        """
        # Audio stream events
        if isinstance(event, AudioStart):
            logger.debug("Audio stream started")
            return None

        if isinstance(event, AudioChunk):
            logger.debug(f"Received audio chunk: {len(event.audio)} bytes")
            return None

        if isinstance(event, AudioStop):
            logger.debug("Audio stream stopped")
            return None

        # Speech recognition events
        if isinstance(event, Transcribe):
            logger.debug("Transcription requested")
            return None

        if isinstance(event, Transcript):
            logger.info(f"Received transcript: {event.text}")
            return await self._process_transcript(event)

        logger.debug(f"Unhandled event type: {type(event).__name__}")
        return None

    async def _process_transcript(self, transcript: Transcript) -> Optional[Event]:
        """Process a transcript event and generate a response.

        Args:
            transcript: The transcript event from the device

        Returns:
            A Synthesize event with the response to speak
        """
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

        This method validates Ollama connectivity before starting the server
        to provide early error detection.

        Raises:
            RuntimeError: If Ollama is not accessible
        """
        # Validate Ollama connection before starting
        if not await self._validate_ollama_connection():
            raise RuntimeError(
                "Ollama is not accessible. Please start it first with: ollama serve"
            )

        logger.info(f"Starting Wyoming server on {self.host}:{self.port}")
        await self.start(self.host, self.port)
