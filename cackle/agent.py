"""
LangChain Agent Management.

This module handles the initialization and execution of the LangChain agent
that powers the voice assistant's intelligent response generation.
"""

import asyncio
import logging
from typing import Optional

from langchain_classic.agents import initialize_agent, AgentExecutor
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI

from cackle.observability import ObservabilityHandler
from cackle.tools import get_available_tools

logger = logging.getLogger(__name__)


class VoiceAssistantAgent:
    """Manages the LangChain agent for intelligent response generation.

    This class encapsulates all agent-related functionality, making it easy to
    swap out implementations or extend with new features like persistent memory,
    different LLM backends, or additional tools.

    Attributes:
        llm: The language model (ChatOpenAI connected to Ollama)
        memory: Conversation memory buffer
        agent: The LangChain agent executor
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434/v1",
        ollama_model: str = "llama3.1:8b",
        ollama_temperature: float = 0.7,
        conversation_window_size: int = 3,
        debug: bool = False,
    ):
        """Initialize the voice assistant agent.

        Args:
            ollama_base_url: Base URL for Ollama's OpenAI-compatible API
            ollama_model: The model name to use from Ollama
            ollama_temperature: Temperature parameter for response generation (0.0-1.0)
            conversation_window_size: Number of messages to keep in conversation memory
            debug: Enable debug mode with detailed observability logging
        """
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.ollama_temperature = ollama_temperature
        self.conversation_window_size = conversation_window_size
        self.debug = debug

        # Initialize the language model
        self.llm = ChatOpenAI(
            base_url=ollama_base_url,
            api_key="ollama",
            model=ollama_model,
            temperature=ollama_temperature,
        )

        # Initialize conversation memory (keeps last N exchanges)
        self.memory = ConversationBufferWindowMemory(
            k=conversation_window_size,
            memory_key="chat_history",
            return_messages=True,
        )

        # Set up callbacks for observability
        callbacks = []
        if debug:
            callbacks.append(ObservabilityHandler())

        # Get available tools and initialize the agent
        tools = get_available_tools()
        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent="chat-zero-shot-react-description",
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            callbacks=callbacks,
        )

        logger.info(
            f"Agent initialized with model '{ollama_model}' "
            f"at {ollama_base_url}"
        )
        if debug:
            logger.info("Debug mode enabled with observability logging")

    async def process_input(self, user_input: str) -> str:
        """Process user input through the agent.

        This method runs the agent in a thread pool to avoid blocking the async event loop.

        Args:
            user_input: The user's text input (transcript from voice recognition)

        Returns:
            The agent's response text

        Raises:
            RuntimeError: If there's an error processing the input
        """
        try:
            logger.debug(f"Processing user input: {user_input}")

            # Run the agent in a thread pool since it's synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self.agent.run, user_input
            )

            logger.info(f"Agent response: {response}")
            return response

        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            raise RuntimeError(f"Agent processing failed: {str(e)}") from e

    def reset_memory(self) -> None:
        """Reset the conversation memory.

        Useful when starting a new conversation or if the memory becomes unwieldy.
        """
        self.memory.clear()
        logger.info("Conversation memory reset")

    def get_memory_summary(self) -> str:
        """Get a summary of the conversation memory.

        Returns:
            String containing the conversation history
        """
        try:
            return self.memory.buffer
        except AttributeError:
            # Fallback if buffer attribute doesn't exist
            return "Memory not available"
