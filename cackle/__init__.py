"""
Cackle Agent - A conversational AI agent with tool use and memory.

This library provides a protocol-agnostic conversational agent powered by
LangChain and local LLMs (via Ollama). It includes:

- Core agent with conversation memory
- Tool/skill system for extending capabilities
- Protocol adapters (Wyoming, and more in future)
- Observability and debugging support

Quick Start:
    >>> from cackle.agent import VoiceAssistantAgent
    >>> agent = VoiceAssistantAgent(
    ...     ollama_base_url="http://localhost:11434/v1",
    ...     ollama_model="llama3.1:8b"
    ... )
    >>> response = await agent.process_input("What time is it?")

For protocol-specific usage, see the adapters:
    >>> from cackle.adapters.wyoming import VoiceAssistantServer
"""

from cackle.agent import VoiceAssistantAgent
from cackle.config import Settings, get_settings
from cackle.tools import get_available_tools

__version__ = "0.1.0"
__all__ = ["VoiceAssistantAgent", "Settings", "get_settings", "get_available_tools"]
