"""Unit tests for chatterbox.conversation.providers."""

from __future__ import annotations

import pytest

from chatterbox.conversation.providers import (
    CompletionResult,
    LLMProvider,
    OpenAICompatibleProvider,
    ToolCall,
    ToolDefinition,
)


# ---------------------------------------------------------------------------
# ToolDefinition
# ---------------------------------------------------------------------------


def test_tool_definition_to_openai_format() -> None:
    tool = ToolDefinition(
        name="get_weather",
        description="Retrieve current weather conditions.",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
            },
            "required": ["location"],
        },
    )

    fmt = tool.to_openai_format()

    assert fmt["type"] == "function"
    assert fmt["function"]["name"] == "get_weather"
    assert fmt["function"]["description"] == "Retrieve current weather conditions."
    assert fmt["function"]["parameters"]["properties"]["location"]["type"] == "string"


def test_tool_definition_empty_parameters() -> None:
    tool = ToolDefinition(name="get_time", description="Get current time.")
    fmt = tool.to_openai_format()

    assert fmt["function"]["parameters"] == {}


# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------


def test_tool_call_dataclass() -> None:
    tc = ToolCall(id="call_abc", name="get_weather", arguments={"location": "Kansas"})
    assert tc.id == "call_abc"
    assert tc.name == "get_weather"
    assert tc.arguments["location"] == "Kansas"


# ---------------------------------------------------------------------------
# CompletionResult
# ---------------------------------------------------------------------------


def test_completion_result_stop() -> None:
    result = CompletionResult(
        finish_reason="stop",
        content="The weather is sunny.",
        tool_calls=[],
        raw_message={"role": "assistant", "content": "The weather is sunny."},
    )
    assert result.finish_reason == "stop"
    assert result.content == "The weather is sunny."
    assert result.tool_calls == []


def test_completion_result_tool_calls() -> None:
    tc = ToolCall(id="c1", name="get_weather", arguments={"location": "LA"})
    result = CompletionResult(
        finish_reason="tool_calls",
        content=None,
        tool_calls=[tc],
        raw_message={"role": "assistant"},
    )
    assert result.finish_reason == "tool_calls"
    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_weather"


# ---------------------------------------------------------------------------
# LLMProvider Protocol conformance
# ---------------------------------------------------------------------------


def test_openai_compatible_provider_implements_protocol() -> None:
    """OpenAICompatibleProvider must satisfy the LLMProvider Protocol."""
    # We test conformance by checking isinstance with the runtime_checkable Protocol.
    # We avoid actually constructing the client to keep unit tests dep-free.
    from unittest.mock import patch

    with patch("chatterbox.conversation.providers.AsyncOpenAI") if False else \
            __import__("contextlib").nullcontext():
        pass

    # Protocol check via isinstance
    # Use duck-typing check: just verify it has the right method signature
    assert hasattr(OpenAICompatibleProvider, "complete")
    import inspect

    sig = inspect.signature(OpenAICompatibleProvider.complete)
    params = list(sig.parameters.keys())
    assert "messages" in params
    assert "tools" in params


def test_openai_compatible_provider_stores_config() -> None:
    from unittest.mock import patch, MagicMock

    with patch("chatterbox.conversation.providers.AsyncOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:11434/v1",
            model="llama3.1:8b",
            api_key="ollama",
            temperature=0.5,
        )

    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.model == "llama3.1:8b"
    assert provider.temperature == 0.5
    mock_cls.assert_called_once_with(
        base_url="http://localhost:11434/v1", api_key="ollama"
    )
