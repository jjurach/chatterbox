"""
LLM Provider abstractions for the Chatterbox conversation package.

Defines the `LLMProvider` Protocol so the `AgenticLoop` can work with any
OpenAI-compatible backend (Ollama, OpenAI, Claude via LiteLLM proxy, etc.)
without being tied to a specific vendor or SDK.

The concrete implementation, `OpenAICompatibleProvider`, uses `openai.AsyncOpenAI`
which supports any OpenAI-compatible base URL.

Also provides:
- Custom exception hierarchy for LLM API errors.
- ``UsageStats`` / ``CostEstimator`` for token usage and cost tracking.
- ``RateLimiter`` for client-side call-rate throttling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Base exception for all LLM provider errors."""


class LLMRateLimitError(LLMError):
    """Raised when the LLM API returns a rate-limit (429) response."""


class LLMConnectionError(LLMError):
    """Raised when the LLM API endpoint cannot be reached."""


class LLMAPIError(LLMError):
    """Raised for other LLM API errors (e.g., 5xx, authentication failures).

    Attributes:
        status_code: HTTP status code from the API, or ``None`` if unavailable.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Usage statistics and cost estimation
# ---------------------------------------------------------------------------


@dataclass
class UsageStats:
    """Token usage recorded for a single LLM completion call.

    Attributes:
        prompt_tokens: Number of input tokens consumed.
        completion_tokens: Number of output tokens generated.
        total_tokens: Combined token count.
        estimated_cost_usd: Estimated cost in USD, or ``None`` if the model is
            not in the ``CostEstimator`` database.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None = None


# (input_per_1k_tokens, output_per_1k_tokens) in USD
_MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.000150, 0.000600),
    "gpt-4-turbo": (0.010, 0.030),
    "gpt-4": (0.030, 0.060),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    # Claude models accessed via LiteLLM proxy use the same model IDs.
    "claude-3-5-haiku-20241022": (0.001, 0.005),
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
    "claude-3-opus-20240229": (0.015, 0.075),
    "claude-haiku-4-5-20251001": (0.001, 0.005),
    "claude-sonnet-4-5": (0.003, 0.015),
    "claude-opus-4-6": (0.015, 0.075),
    "claude-sonnet-4-6": (0.003, 0.015),
}


class CostEstimator:
    """Estimates USD cost for an LLM completion based on token counts.

    Uses a built-in model-cost database. Unknown models return ``None`` for
    ``estimated_cost_usd`` rather than raising an error.

    The database includes common OpenAI and Claude (via LiteLLM) models.
    Costs are approximate and may lag actual provider pricing.
    """

    def estimate(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float | None:
        """Estimate cost in USD for a single completion call.

        Args:
            model: Model identifier (e.g. ``"gpt-4o"``).
            prompt_tokens: Input token count.
            completion_tokens: Output token count.

        Returns:
            Estimated cost in USD, or ``None`` if the model is not in the
            database.
        """
        costs = _MODEL_COSTS.get(model)
        if costs is None:
            return None
        input_cost_per_1k, output_cost_per_1k = costs
        return (
            prompt_tokens * input_cost_per_1k / 1000.0
            + completion_tokens * output_cost_per_1k / 1000.0
        )


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Async client-side rate limiter using a sliding window.

    Enforces a maximum number of calls per minute. Callers ``await
    acquire()`` before making an LLM request; the method sleeps until
    the window allows another call.

    This is a *client-side* limiter that complements (but does not replace)
    the server-side rate limiting enforced by the API provider.

    Attributes:
        calls_per_minute: Maximum calls allowed in any 60-second window.
    """

    def __init__(self, calls_per_minute: int) -> None:
        if calls_per_minute <= 0:
            raise ValueError("calls_per_minute must be a positive integer.")
        self.calls_per_minute = calls_per_minute
        self._window_seconds = 60.0
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a call slot is available within the current window.

        Should be called at the start of each LLM API request.
        """
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_seconds

            # Prune timestamps older than the window.
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.calls_per_minute:
                # Oldest call in window determines how long to sleep.
                sleep_until = self._timestamps[0] + self._window_seconds
                sleep_secs = sleep_until - time.monotonic()
                if sleep_secs > 0:
                    logger.debug(
                        "RateLimiter: at capacity (%d/%d), sleeping %.2fs",
                        len(self._timestamps),
                        self.calls_per_minute,
                        sleep_secs,
                    )
                    await asyncio.sleep(sleep_secs)
                # Prune again after sleeping.
                now = time.monotonic()
                cutoff = now - self._window_seconds
                while self._timestamps and self._timestamps[0] < cutoff:
                    self._timestamps.popleft()

            self._timestamps.append(time.monotonic())


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


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
        usage: Token usage and cost for this call, or ``None`` if unavailable.
    """

    finish_reason: str
    content: str | None
    tool_calls: list[ToolCall]
    raw_message: dict[str, Any]
    usage: UsageStats | None = None


# ---------------------------------------------------------------------------
# LLMProvider Protocol
# ---------------------------------------------------------------------------


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

        Raises:
            LLMRateLimitError: If the API returns a 429 rate-limit response.
            LLMConnectionError: If the API endpoint cannot be reached.
            LLMAPIError: For other API-level failures.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete provider implementation
# ---------------------------------------------------------------------------


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
        rate_limiter: Optional ``RateLimiter`` for client-side call throttling.
        cost_estimator: Optional ``CostEstimator`` for tracking USD cost.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.1:8b",
        api_key: str = "ollama",
        temperature: float = 0.7,
        rate_limiter: RateLimiter | None = None,
        cost_estimator: CostEstimator | None = None,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.rate_limiter = rate_limiter
        self.cost_estimator = cost_estimator
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
    ) -> CompletionResult:
        """Call the LLM and return a structured `CompletionResult`.

        Raises:
            LLMRateLimitError: If the API returns a 429 response.
            LLMConnectionError: If the API endpoint cannot be reached.
            LLMAPIError: For other API-level failures (e.g. 4xx/5xx).
        """
        if self.rate_limiter is not None:
            await self.rate_limiter.acquire()

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

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            logger.warning("LLM rate limit exceeded: %s", exc)
            raise LLMRateLimitError(f"Rate limit exceeded: {exc}") from exc
        except APIConnectionError as exc:
            logger.error("LLM connection failed: %s", exc)
            raise LLMConnectionError(f"Could not connect to LLM endpoint: {exc}") from exc
        except APIStatusError as exc:
            logger.error("LLM API error %d: %s", exc.status_code, exc)
            raise LLMAPIError(
                f"LLM API returned status {exc.status_code}: {exc}",
                status_code=exc.status_code,
            ) from exc

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

        # Build usage stats if the response includes token counts.
        usage: UsageStats | None = None
        if response.usage is not None:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            estimated_cost: float | None = None
            if self.cost_estimator is not None:
                estimated_cost = self.cost_estimator.estimate(
                    self.model, prompt_tokens, completion_tokens
                )
            usage = UsageStats(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
            )

        logger.debug(
            "LLM response: finish_reason=%s, tool_calls=%d, tokens=%s",
            finish_reason,
            len(tool_calls),
            usage.total_tokens if usage else "n/a",
        )

        return CompletionResult(
            finish_reason=finish_reason,
            content=message.content,
            tool_calls=tool_calls,
            raw_message=raw_message,
            usage=usage,
        )
