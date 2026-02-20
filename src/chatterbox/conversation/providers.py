"""
LLM Provider abstractions for the Chatterbox conversation package.

Defines the `LLMProvider` Protocol so the `AgenticLoop` can work with any
OpenAI-compatible backend (Ollama, OpenAI, Claude via LiteLLM proxy, etc.)
without being tied to a specific vendor or SDK.

The concrete implementation, `OpenAICompatibleProvider`, uses `openai.AsyncOpenAI`
which supports any OpenAI-compatible base URL.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Describes a callable tool available to the LLM.

    This mirrors the OpenAI function-calling tool definition format, which is
    also the format expected by the HA LLM API helper when integrating as a
    ConversationEntity.

    Attributes:
        name: The tool's unique name (used by the LLM to invoke it).
        description: Human-readable description shown in the LLM's tool prompt.
        parameters: JSON Schema dict describing the tool's input parameters.
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_openai_format(self) -> dict[str, Any]:
        """Serialise to OpenAI tool definition format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolCall:
    """A tool invocation requested by the LLM.

    Attributes:
        id: Unique call ID returned by the LLM (used to correlate the result).
        name: Name of the tool to invoke.
        arguments: Parsed JSON arguments dict.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class CompletionResult:
    """Result of a single LLM completion call.

    The loop checks `finish_reason` to determine whether to return the final
    text or continue dispatching tool calls.

    Attributes:
        finish_reason: ``"stop"`` for a final text response, ``"tool_calls"``
            when the LLM wants to invoke tools.
        content: Final text response (populated when finish_reason == "stop").
        tool_calls: Requested tool invocations (populated when finish_reason
            == "tool_calls").
        raw_message: The raw assistant message dict (for appending to history).
    """

    finish_reason: str
    content: str | None
    tool_calls: list[ToolCall]
    raw_message: dict[str, Any]


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM backends used by AgenticLoop.

    Any object implementing this Protocol can serve as the LLM backend.
    The default implementation is `OpenAICompatibleProvider`.
    """

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
    ) -> CompletionResult:
        """Send a completion request to the LLM.

        Args:
            messages: The full conversation history in OpenAI message format.
            tools: The available tool definitions.

        Returns:
            A `CompletionResult` describing the LLM's response.
        """
        ...


class OpenAICompatibleProvider:
    """LLM provider backed by any OpenAI-compatible endpoint.

    Works with:
    - Ollama (``http://localhost:11434/v1``)
    - OpenAI (``https://api.openai.com/v1``)
    - Claude via LiteLLM proxy
    - Any other OpenAI-compatible API

    Attributes:
        base_url: The API base URL.
        model: The model identifier.
        api_key: API key (use ``"ollama"`` for Ollama with no auth).
        temperature: Sampling temperature (0.0–2.0).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.1:8b",
        api_key: str = "ollama",
        temperature: float = 0.7,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
    ) -> CompletionResult:
        """Call the LLM and return a structured `CompletionResult`."""
        openai_tools = [t.to_openai_format() for t in tools] if tools else []

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        logger.debug(
            "LLM request: model=%s, messages=%d, tools=%d",
            self.model,
            len(messages),
            len(openai_tools),
        )

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        finish_reason = choice.finish_reason or "stop"
        message = choice.message

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        # Build the raw assistant message for appending to history
        raw_message: dict[str, Any] = {"role": "assistant"}
        if message.content is not None:
            raw_message["content"] = message.content
        if tool_calls:
            raw_message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in tool_calls
            ]

        logger.debug(
            "LLM response: finish_reason=%s, tool_calls=%d",
            finish_reason,
            len(tool_calls),
        )

        return CompletionResult(
            finish_reason=finish_reason,
            content=message.content,
            tool_calls=tool_calls,
            raw_message=raw_message,
        )
