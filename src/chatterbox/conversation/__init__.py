"""
Chatterbox Conversation Package.

Implements the agentic tool-calling loop and Home Assistant ConversationEntity
skeleton for LLM integration.

Architecture decision: Task 4.2 selected a custom minimal async loop using the
OpenAI-compatible SDK (`openai.AsyncOpenAI`) rather than LangGraph or LangChain.
See docs/agentic-framework-evaluation.md for rationale.
"""

from chatterbox.conversation.entity import (
    ChatterboxConversationEntity,
    ConversationInput,
    ConversationResult,
)
from chatterbox.conversation.loop import AgenticLoop, ToolDispatcher
from chatterbox.conversation.providers import (
    CompletionResult,
    LLMProvider,
    OpenAICompatibleProvider,
    ToolCall,
    ToolDefinition,
)

__all__ = [
    "AgenticLoop",
    "ChatterboxConversationEntity",
    "CompletionResult",
    "ConversationInput",
    "ConversationResult",
    "LLMProvider",
    "OpenAICompatibleProvider",
    "ToolCall",
    "ToolDefinition",
    "ToolDispatcher",
]
