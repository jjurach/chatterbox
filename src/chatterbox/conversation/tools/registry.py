"""
Tool registry for the Chatterbox agentic loop.

Provides ``ToolRegistry``, a container for registering tool handlers and
building a dispatcher callable with optional timeout and retry support.

Typical usage::

    from chatterbox.conversation.tools.registry import ToolRegistry
    from chatterbox.conversation.tools.weather import WeatherTool
    from chatterbox.conversation.tools.datetime_tool import DateTimeTool

    registry = ToolRegistry()

    weather = WeatherTool()
    registry.register(WeatherTool.TOOL_DEFINITION, weather.as_dispatcher_entry())

    dt = DateTimeTool()
    registry.register(DateTimeTool.TOOL_DEFINITION, dt.as_dispatcher_entry())

    dispatcher = registry.build_dispatcher(timeout=10.0, max_retries=1)
    loop = AgenticLoop(
        provider=provider,
        tool_dispatcher=dispatcher,
    )
    result = await loop.run(
        user_text="What is the weather in Kansas?",
        chat_history=[],
        tools=registry.get_definitions(),
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from chatterbox.conversation.providers import ToolDefinition

logger = logging.getLogger(__name__)

# Type alias for a single tool handler: async (args_dict) -> result_str
AsyncToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


class ToolRegistry:
    """Registry mapping tool names to their definitions and async handlers.

    Manages a ``name -> (ToolDefinition, AsyncToolHandler)`` mapping.
    Use ``get_definitions()`` to obtain the list of ``ToolDefinition`` objects
    for ``AgenticLoop.run()``, and ``build_dispatcher()`` to produce the
    dispatcher callable for ``AgenticLoop.__init__()``.

    Attributes:
        _tools: Internal dict of registered tool entries.
    """

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolDefinition, AsyncToolHandler]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        definition: ToolDefinition,
        handler: AsyncToolHandler,
    ) -> None:
        """Register a tool with its async handler.

        Args:
            definition: The tool's ``ToolDefinition`` (name, description,
                parameters).
            handler: Async callable ``(args: dict) -> str`` that executes
                the tool and returns a JSON string result.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if definition.name in self._tools:
            raise ValueError(
                f"Tool {definition.name!r} is already registered. "
                "Deregister it first before re-registering."
            )
        self._tools[definition.name] = (definition, handler)
        logger.debug("Registered tool: %r", definition.name)

    def deregister(self, name: str) -> None:
        """Remove a registered tool by name.

        Args:
            name: The tool name to remove.

        Raises:
            KeyError: If the tool is not registered.
        """
        if name not in self._tools:
            raise KeyError(f"Tool {name!r} is not registered.")
        del self._tools[name]
        logger.debug("Deregistered tool: %r", name)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_definitions(self) -> list[ToolDefinition]:
        """Return all registered ``ToolDefinition`` objects (insertion order)."""
        return [defn for defn, _handler in self._tools.values()]

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Return True if *name* is a registered tool."""
        return name in self._tools

    # ------------------------------------------------------------------
    # Dispatcher factory
    # ------------------------------------------------------------------

    def build_dispatcher(
        self,
        timeout: float | None = 30.0,
        max_retries: int = 0,
        retry_exceptions: tuple[type[BaseException], ...] = (asyncio.TimeoutError,),
    ) -> Callable[[str, dict[str, Any]], Awaitable[str]]:
        """Build an async dispatcher compatible with ``AgenticLoop.tool_dispatcher``.

        The returned callable wraps each tool invocation with:

        - **Timeout** — ``asyncio.wait_for(handler(...), timeout=timeout)``
          if *timeout* is set.
        - **Retry** — re-attempts the call up to *max_retries* additional times
          when the exception is an instance of *retry_exceptions*.
          Non-retryable exceptions propagate immediately so the ``AgenticLoop``
          can record the error.

        Args:
            timeout: Maximum seconds per tool call.  ``None`` disables the
                timeout.  Default: ``30.0``.
            max_retries: Number of *additional* attempts on retryable failures.
                ``0`` means a single attempt only (no retries).
            retry_exceptions: Exception types that trigger a retry.
                Defaults to ``(asyncio.TimeoutError,)`` for transient timeout
                failures.

        Returns:
            An async callable ``(name, args) -> str`` suitable for
            ``AgenticLoop.tool_dispatcher``.  Unknown tool names return a JSON
            ``{"error": ...}`` string rather than raising.
        """
        # Snapshot the registry at build time — later registrations are not
        # reflected in this dispatcher.
        registry_snapshot = dict(self._tools)
        total_attempts = max_retries + 1

        async def _dispatch(name: str, args: dict[str, Any]) -> str:
            entry = registry_snapshot.get(name)
            if entry is None:
                logger.warning("Unknown tool requested: %r", name)
                return json.dumps({"error": f"Unknown tool: {name!r}"})

            _definition, handler = entry

            for attempt in range(1, total_attempts + 1):
                try:
                    if timeout is not None:
                        result = await asyncio.wait_for(
                            handler(args), timeout=timeout
                        )
                    else:
                        result = await handler(args)
                    return result
                except BaseException as exc:
                    is_retryable = retry_exceptions and isinstance(exc, retry_exceptions)
                    has_attempts_left = attempt < total_attempts
                    if is_retryable and has_attempts_left:
                        logger.warning(
                            "Tool %r attempt %d/%d failed (%s: %s); retrying…",
                            name,
                            attempt,
                            total_attempts,
                            type(exc).__name__,
                            exc,
                        )
                        continue
                    # Either non-retryable or last attempt — propagate so the
                    # AgenticLoop can wrap it in a tool-result error message.
                    raise

            # Unreachable, but keeps type checkers happy.
            raise RuntimeError("build_dispatcher: retry loop exited unexpectedly")  # pragma: no cover

        return _dispatch
