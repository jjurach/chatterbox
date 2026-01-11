"""
Wyoming Voice Assistant Server with LangChain Integration

A Wyoming protocol server for the ESP32-S3-BOX-3B voice assistant.
This server integrates LangChain with a local Ollama LLM for intelligent responses.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from langchain.agents import AgentExecutor, Tool, initialize_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
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


def get_time() -> str:
    """Get the current time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class VoiceAssistantServer(AsyncServer):
    """Wyoming server implementation for voice assistant with LangChain integration."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 10700,
        ollama_base_url: str = "http://localhost:11434/v1",
    ):
        """
        Initialize the voice assistant server with LangChain agent.

        Args:
            host: The host to bind to (default: 0.0.0.0)
            port: The port to bind to (default: 10700)
            ollama_base_url: The base URL for Ollama's OpenAI-compatible API
        """
        super().__init__()
        self.host = host
        self.port = port
        self.ollama_base_url = ollama_base_url

        # Initialize LangChain components
        self.llm = ChatOpenAI(
            base_url=ollama_base_url,
            api_key="ollama",
            model="llama3.1:8b",
            temperature=0.7,
        )

        # Initialize conversation memory (last 3 exchanges)
        self.memory = ConversationBufferWindowMemory(
            k=3, memory_key="chat_history", return_messages=True
        )

        # Define tools for the agent
        tools = [
            Tool(
                name="GetTime",
                func=get_time,
                description="Useful for when you need to know the current time or date.",
            ),
        ]

        # Initialize the agent with ReAct (Reasoning + Acting) approach
        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent="chat-zero-shot-react-description",
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
        )

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
            # For now, respond with a default message
            # In a full implementation, you would do STT here or receive transcript separately
            return self._create_response("I received your audio, but I need to implement STT.")

        # Try to handle custom transcript events
        # This would be sent by the device after it performs STT
        if hasattr(event, "text") and hasattr(event, "__class__"):
            text = getattr(event, "text", None)
            if text:
                logger.info(f"Processing transcript: {text}")
                return await self._process_user_input(text)

        logger.debug(f"Unhandled event type: {type(event)}")
        return None

    async def _process_user_input(self, user_input: str) -> Optional[Event]:
        """
        Process user input through the LangChain agent.

        Args:
            user_input: The user's text input (transcript)

        Returns:
            A Synthesize event with the agent's response
        """
        try:
            # Run the agent with the user input
            # Note: initialize_agent returns a synchronous executor, so we run it in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self.agent.run, user_input
            )

            logger.info(f"Agent response: {response}")
            return self._create_response(response)

        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return self._create_response(f"Sorry, I encountered an error: {str(e)}")

    def _create_response(self, text: str) -> Synthesize:
        """
        Create a TTS (Text-to-Speech) event with the given text.

        Args:
            text: The text to synthesize

        Returns:
            A Synthesize event configured to speak the response text
        """
        return Synthesize(
            text=text,
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
