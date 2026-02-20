"""
AgenticLoop — the minimal async tool-calling engine for Chatterbox.

This module implements the core "agentic" behaviour: calling the LLM,
dispatching tool calls the LLM requests, feeding results back, and
repeating until the LLM produces a final text response.

Design decision (Task 4.2): A custom loop using `openai.AsyncOpenAI` was
selected over LangGraph/LangChain because the tool-calling pattern here is
linear (no branching, no multi-agent). See docs/agentic-framework-evaluation.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable

from chatterbox.conversation.providers import (
    CompletionResult,
    LLMProvider,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)

# Callable type for async tool dispatcher functions.
# Receives (tool_name, tool_arguments) and returns a string result.
ToolDispatcher = Callable[[str, dict[str, Any]], Awaitable[str]]


class AgenticLoop:
    """Executes the LLM + tool-calling loop for a single conversation turn.

    The loop runs until the LLM returns ``finish_reason == "stop"`` or
    ``max_iterations`` is reached.

    Typical usage inside a ConversationEntity::

        loop = AgenticLoop(provider=my_provider, tool_dispatcher=my_dispatcher)
        response_text = await loop.run(
            user_text="What is the weather in Kansas?",
            chat_history=[],
            tools=[weather_tool_def],
        )

    Attributes:
        provider: The LLM backend (any `LLMProvider` implementation).
        tool_dispatcher: Async callable ``(name, args) → result_str`` that
            executes tool calls.
        max_iterations: Maximum number of LLM calls per turn (guard against
            infinite loops). Default: 10.
        system_prompt: Optional system message prepended to every turn.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_dispatcher: ToolDispatcher,
        max_iterations: int = 10,
        system_prompt: str | None = None,
    ) -> None:
        self.provider = provider
        self.tool_dispatcher = tool_dispatcher
        self.max_iterations = max_iterations
        self.system_prompt = system_prompt

    async def run(
        self,
        user_text: str,
        chat_history: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
    ) -> str:
        """Run one conversation turn through the agentic loop.

        Args:
            user_text: The user's transcribed utterance.
            chat_history: Prior conversation messages in OpenAI format.
                These are not mutated; the loop works on a local copy.
            tools: Tool definitions available for this turn. If ``None``
                or empty, the LLM is called without tools.

        Returns:
            The LLM's final text response for this turn.

        Raises:
            RuntimeError: If ``max_iterations`` is exceeded before the LLM
                produces a ``"stop"`` response.
        """
        tools = tools or []
        messages: list[dict[str, Any]] = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        messages.extend(chat_history)
        messages.append({"role": "user", "content": user_text})

        turn_start = time.monotonic()

        for iteration in range(self.max_iterations):
            logger.debug("Agentic loop iteration %d/%d", iteration + 1, self.max_iterations)

            llm_t0 = time.monotonic()
            result: CompletionResult = await self.provider.complete(messages, tools)
            logger.debug(
                "LLM call %d took %.3fs (finish_reason=%s)",
                iteration + 1,
                time.monotonic() - llm_t0,
                result.finish_reason,
            )

            if result.finish_reason == "stop":
                response_text = result.content or ""
                logger.info(
                    "Loop complete after %d iteration(s) in %.3fs",
                    iteration + 1,
                    time.monotonic() - turn_start,
                )
                return response_text

            if result.finish_reason == "tool_calls" and result.tool_calls:
                # Append assistant message with tool_calls
                messages.append(result.raw_message)

                # Dispatch all tool calls concurrently and collect results
                tools_t0 = time.monotonic()
                tool_result_messages = await self._dispatch_tool_calls(result.tool_calls)
                logger.debug(
                    "Dispatched %d tool(s) concurrently in %.3fs",
                    len(result.tool_calls),
                    time.monotonic() - tools_t0,
                )
                messages.extend(tool_result_messages)
                continue

            # Unexpected finish_reason — treat content as final response
            logger.warning(
                "Unexpected finish_reason=%r; returning content as-is", result.finish_reason
            )
            return result.content or ""

        raise RuntimeError(
            f"AgenticLoop exceeded max_iterations={self.max_iterations} "
            "without reaching a final response. Check for tool call loops."
        )

    async def _dispatch_tool_calls(
        self, tool_calls: list[ToolCall]
    ) -> list[dict[str, Any]]:
        """Dispatch a list of tool calls concurrently and return tool result messages.

        All tool calls in the list are launched simultaneously via
        ``asyncio.gather``, reducing latency when the LLM requests multiple
        tools in a single response.

        Args:
            tool_calls: The tool invocations requested by the LLM.

        Returns:
            A list of OpenAI-format tool result messages to append to the
            conversation history.  Order matches the order of *tool_calls*.
        """

        async def _run_one(tc: ToolCall) -> dict[str, Any]:
            logger.debug("Dispatching tool: %s(%s)", tc.name, tc.arguments)
            try:
                result_str = await self.tool_dispatcher(tc.name, tc.arguments)
            except Exception as exc:
                logger.error("Tool %r failed: %s", tc.name, exc, exc_info=True)
                result_str = json.dumps({"error": str(exc)})
            return {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            }

        return list(await asyncio.gather(*[_run_one(tc) for tc in tool_calls]))
