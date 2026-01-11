"""
Wyoming Voice Assistant Server

A simple Wyoming protocol server for the ESP32-S3-BOX-3B voice assistant.
This server receives audio from the device and responds with synthetic speech.
"""

import asyncio
import logging
from typing import Optional

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.server import AsyncServer
from wyoming.tts import Synthesize, SynthesizeVoice
from wyoming.voice import Voice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Placeholder for LangChain integration
# Example usage would be:
# from langchain.llms import OpenAI
# from langchain.chains import LLMChain
# from langchain.prompts import PromptTemplate
#
# llm = OpenAI(temperature=0)
# prompt = PromptTemplate(input_variables=["user_input"], template="...")
# chain = LLMChain(llm=llm, prompt=prompt)


class VoiceAssistantServer(AsyncServer):
    """Wyoming server implementation for voice assistant."""

    def __init__(self, host: str = "0.0.0.0", port: int = 10700):
        """
        Initialize the voice assistant server.

        Args:
            host: The host to bind to (default: 0.0.0.0)
            port: The port to bind to (default: 10700)
        """
        super().__init__()
        self.host = host
        self.port = port

    async def handle_event(self, event: Event) -> Optional[Event]:
        """
        Handle incoming Wyoming events from the ESP32 device.

        Args:
            event: The incoming event from the client

        Returns:
            An optional response event to send back to the client
        """
        if isinstance(event, AudioStart):
            logger.info("Audio stream started")
            return None

        if isinstance(event, AudioChunk):
            logger.debug(f"Received audio chunk: {len(event.audio)} bytes")
            return None

        if isinstance(event, AudioStop):
            logger.info("Audio stream stopped")
            # Respond with a TTS event containing "Hello world"
            return self._create_hello_world_response()

        logger.debug(f"Unhandled event type: {type(event)}")
        return None

    def _create_hello_world_response(self) -> Synthesize:
        """
        Create a TTS (Text-to-Speech) event to speak 'Hello world'.

        Returns:
            A Synthesize event configured to speak the response text
        """
        return Synthesize(
            text="Hello world",
            voice=SynthesizeVoice(
                name="default",
                language="en-US",
                speaker="default",
            ),
        )

    async def run(self) -> None:
        """Start the Wyoming server and listen for incoming connections."""
        logger.info(f"Starting Wyoming server on {self.host}:{self.port}")
        await self.listen(self.host, self.port)


async def main() -> None:
    """Main entry point for the Wyoming server."""
    server = VoiceAssistantServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
