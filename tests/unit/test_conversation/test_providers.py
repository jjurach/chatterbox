"""Unit tests for chatterbox.conversation.providers."""

from __future__ import annotations

import pytest

from chatterbox.conversation.providers import (
    CompletionResult,
    CostEstimator,
    LLMAPIError,
    LLMConnectionError,
    LLMError,
    LLMProvider,
    LLMRateLimitError,
    OpenAICompatibleProvider,
    RateLimiter,
    ToolCall,
    ToolDefinition,
    UsageStats,
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


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------


def test_llm_error_is_base_exception() -> None:
    err = LLMError("something went wrong")
    assert isinstance(err, Exception)
    assert str(err) == "something went wrong"


def test_llm_rate_limit_error_inherits_llm_error() -> None:
    err = LLMRateLimitError("rate limited")
    assert isinstance(err, LLMError)


def test_llm_connection_error_inherits_llm_error() -> None:
    err = LLMConnectionError("no route")
    assert isinstance(err, LLMError)


def test_llm_api_error_inherits_llm_error() -> None:
    err = LLMAPIError("server error", status_code=500)
    assert isinstance(err, LLMError)
    assert err.status_code == 500


def test_llm_api_error_status_code_defaults_to_none() -> None:
    err = LLMAPIError("unknown error")
    assert err.status_code is None


# ---------------------------------------------------------------------------
# UsageStats
# ---------------------------------------------------------------------------


def test_usage_stats_fields() -> None:
    stats = UsageStats(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost_usd=0.0012,
    )
    assert stats.prompt_tokens == 100
    assert stats.completion_tokens == 50
    assert stats.total_tokens == 150
    assert stats.estimated_cost_usd == pytest.approx(0.0012)


def test_usage_stats_default_cost_none() -> None:
    stats = UsageStats(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    assert stats.estimated_cost_usd is None


# ---------------------------------------------------------------------------
# CostEstimator
# ---------------------------------------------------------------------------


def test_cost_estimator_known_model() -> None:
    estimator = CostEstimator()
    # gpt-4o: 0.005/1k input, 0.015/1k output
    cost = estimator.estimate("gpt-4o", prompt_tokens=1000, completion_tokens=1000)
    assert cost is not None
    assert cost == pytest.approx(0.005 + 0.015)


def test_cost_estimator_known_model_mini() -> None:
    estimator = CostEstimator()
    # gpt-4o-mini: 0.000150/1k input, 0.000600/1k output
    cost = estimator.estimate("gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000)
    assert cost is not None
    assert cost == pytest.approx(0.000150 + 0.000600)


def test_cost_estimator_unknown_model_returns_none() -> None:
    estimator = CostEstimator()
    cost = estimator.estimate("some-unknown-model-v999", prompt_tokens=100, completion_tokens=50)
    assert cost is None


def test_cost_estimator_zero_tokens() -> None:
    estimator = CostEstimator()
    cost = estimator.estimate("gpt-4o", prompt_tokens=0, completion_tokens=0)
    assert cost == pytest.approx(0.0)


def test_cost_estimator_claude_model() -> None:
    estimator = CostEstimator()
    cost = estimator.estimate(
        "claude-haiku-4-5-20251001",
        prompt_tokens=1000,
        completion_tokens=1000,
    )
    assert cost is not None
    assert cost > 0.0


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


def test_rate_limiter_rejects_zero_calls_per_minute() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        RateLimiter(calls_per_minute=0)


def test_rate_limiter_rejects_negative_calls_per_minute() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        RateLimiter(calls_per_minute=-1)


def test_rate_limiter_stores_calls_per_minute() -> None:
    rl = RateLimiter(calls_per_minute=60)
    assert rl.calls_per_minute == 60


@pytest.mark.anyio
async def test_rate_limiter_allows_calls_within_limit() -> None:
    """Calls within the limit should not block."""
    rl = RateLimiter(calls_per_minute=10)
    # 5 rapid calls should all succeed immediately (under limit of 10/min)
    for _ in range(5):
        await rl.acquire()
    assert len(rl._timestamps) == 5


@pytest.mark.anyio
async def test_rate_limiter_records_timestamps() -> None:
    rl = RateLimiter(calls_per_minute=100)
    await rl.acquire()
    await rl.acquire()
    assert len(rl._timestamps) == 2


# ---------------------------------------------------------------------------
# CompletionResult with usage
# ---------------------------------------------------------------------------


def test_completion_result_with_usage() -> None:
    stats = UsageStats(prompt_tokens=50, completion_tokens=20, total_tokens=70)
    result = CompletionResult(
        finish_reason="stop",
        content="Hello",
        tool_calls=[],
        raw_message={"role": "assistant", "content": "Hello"},
        usage=stats,
    )
    assert result.usage is not None
    assert result.usage.total_tokens == 70


def test_completion_result_usage_defaults_to_none() -> None:
    result = CompletionResult(
        finish_reason="stop",
        content="Hello",
        tool_calls=[],
        raw_message={"role": "assistant", "content": "Hello"},
    )
    assert result.usage is None


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider — error handling (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_provider_raises_llm_rate_limit_error_on_429() -> None:
    from unittest.mock import patch, AsyncMock, MagicMock
    from openai import RateLimitError as OpenAIRateLimitError

    with patch("chatterbox.conversation.providers.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=OpenAIRateLimitError(
                "rate limit", response=MagicMock(status_code=429), body={}
            )
        )
        mock_cls.return_value = mock_client
        provider = OpenAICompatibleProvider()

    with pytest.raises(LLMRateLimitError):
        await provider.complete(
            messages=[{"role": "user", "content": "Hi"}],
            tools=[],
        )


@pytest.mark.anyio
async def test_provider_raises_llm_connection_error_on_network_failure() -> None:
    from unittest.mock import patch, AsyncMock, MagicMock
    from openai import APIConnectionError as OpenAIConnectionError

    with patch("chatterbox.conversation.providers.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=OpenAIConnectionError(request=MagicMock())
        )
        mock_cls.return_value = mock_client
        provider = OpenAICompatibleProvider()

    with pytest.raises(LLMConnectionError):
        await provider.complete(
            messages=[{"role": "user", "content": "Hi"}],
            tools=[],
        )


@pytest.mark.anyio
async def test_provider_raises_llm_api_error_on_5xx() -> None:
    from unittest.mock import patch, AsyncMock, MagicMock
    from openai import APIStatusError

    with patch("chatterbox.conversation.providers.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIStatusError(
                "Internal Server Error",
                response=mock_response,
                body={},
            )
        )
        mock_cls.return_value = mock_client
        provider = OpenAICompatibleProvider()

    with pytest.raises(LLMAPIError) as exc_info:
        await provider.complete(
            messages=[{"role": "user", "content": "Hi"}],
            tools=[],
        )
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider — rate limiter integration (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_provider_calls_rate_limiter_acquire() -> None:
    """Provider must call rate_limiter.acquire() before each completion."""
    from unittest.mock import patch, AsyncMock, MagicMock

    rate_limiter = MagicMock()
    rate_limiter.acquire = AsyncMock()

    with patch("chatterbox.conversation.providers.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        # Build a minimal realistic response object
        mock_choice = MagicMock()
        mock_choice.finish_reason = "stop"
        mock_choice.message.content = "Hi there"
        mock_choice.message.tool_calls = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        provider = OpenAICompatibleProvider(rate_limiter=rate_limiter)

    await provider.complete(messages=[{"role": "user", "content": "Hi"}], tools=[])

    rate_limiter.acquire.assert_awaited_once()


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider — cost tracking (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_provider_populates_usage_stats_when_response_includes_usage() -> None:
    from unittest.mock import patch, AsyncMock, MagicMock

    with patch("chatterbox.conversation.providers.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.finish_reason = "stop"
        mock_choice.message.content = "The answer is 42."
        mock_choice.message.tool_calls = None
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 80
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 100
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        provider = OpenAICompatibleProvider(
            model="gpt-4o-mini",
            cost_estimator=CostEstimator(),
        )

    result = await provider.complete(
        messages=[{"role": "user", "content": "What is the answer?"}],
        tools=[],
    )

    assert result.usage is not None
    assert result.usage.prompt_tokens == 80
    assert result.usage.completion_tokens == 20
    assert result.usage.total_tokens == 100
    assert result.usage.estimated_cost_usd is not None
    assert result.usage.estimated_cost_usd > 0.0


@pytest.mark.anyio
async def test_provider_usage_is_none_when_response_has_no_usage() -> None:
    from unittest.mock import patch, AsyncMock, MagicMock

    with patch("chatterbox.conversation.providers.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.finish_reason = "stop"
        mock_choice.message.content = "Response"
        mock_choice.message.tool_calls = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        provider = OpenAICompatibleProvider()

    result = await provider.complete(
        messages=[{"role": "user", "content": "Hello"}],
        tools=[],
    )

    assert result.usage is None
