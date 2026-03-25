"""
Mellona weather tool adapter for Chatterbox.

This module integrates the Mellona package's WeatherTool into Chatterbox's
tool registry and agentic loop. Mellona provides a high-quality weather tool
implementation using Open-Meteo's free weather API.

Instead of reimplementing weather functionality, this adapter bridges Mellona's
WeatherTool to Chatterbox's ToolDefinition and dispatcher interfaces.

Usage::

    from chatterbox.conversation.tools.mellona_weather import MellonaWeatherAdapter
    from chatterbox.conversation.tools.registry import ToolRegistry

    # Create the adapter
    adapter = MellonaWeatherAdapter()

    # Register it in the tool registry
    registry = ToolRegistry()
    registry.register(
        adapter.tool_definition,
        adapter.as_dispatcher_entry(),
    )

    # Use with AgenticLoop
    dispatcher = registry.build_dispatcher()
    loop = AgenticLoop(
        provider=provider,
        tool_dispatcher=dispatcher,
    )
    result = await loop.run(
        user_text="What's the weather in London?",
        chat_history=[],
        tools=registry.get_definitions(),
    )
"""

from __future__ import annotations

import json
import logging
from typing import Any

from chatterbox.conversation.providers import ToolDefinition

logger = logging.getLogger(__name__)


class MellonaWeatherAdapter:
    """Adapter to integrate Mellona's WeatherTool with Chatterbox.

    The Mellona package provides a high-quality weather tool that queries the
    Open-Meteo API (free, no API key required). This adapter wraps it to work
    with Chatterbox's agentic loop and tool registry.

    Attributes:
        tool_definition: The ToolDefinition for passing to AgenticLoop.
        timeout: HTTP request timeout in seconds (default 10).
    """

    def __init__(self, timeout: float = 10.0) -> None:
        """Initialize the Mellona weather adapter.

        Args:
            timeout: HTTP request timeout for weather API calls in seconds.
        """
        self.timeout = timeout
        self._weather_tool: Any = None
        logger.info("MellonaWeatherAdapter initialized (timeout=%s)", timeout)

    def _get_weather_tool(self) -> Any:
        """Lazily import and instantiate the Mellona WeatherTool.

        Returns:
            An instance of mellona.tools.weather.WeatherTool.

        Raises:
            ImportError: If the mellona package is not installed.
        """
        if self._weather_tool is None:
            try:
                from mellona.tools.weather import WeatherTool as MellonaWeatherTool

                self._weather_tool = MellonaWeatherTool(timeout=self.timeout)
                logger.debug("Mellona WeatherTool loaded")
            except ImportError as exc:
                logger.error(
                    "Failed to import mellona.tools.weather: %s. "
                    "Ensure mellona is installed: pip install mellona",
                    exc,
                )
                raise

        return self._weather_tool

    @property
    def tool_definition(self) -> ToolDefinition:
        """Return the ToolDefinition for this tool.

        Lazily loads the Mellona WeatherTool to extract its TOOL_DEFINITION.

        Returns:
            A ToolDefinition with name, description, and parameters.
        """
        weather_tool = self._get_weather_tool()
        # Mellona's WeatherTool.TOOL_DEFINITION is compatible with Chatterbox's
        # ToolDefinition (same structure: name, description, parameters)
        return weather_tool.TOOL_DEFINITION

    def as_dispatcher_entry(self):
        """Return an async callable for use inside a ToolDispatcher.

        The returned callable handles tool invocation, error handling, and
        response formatting.

        Returns:
            An async callable ``(args: dict[str, Any]) -> str`` that executes
            the weather tool and returns a JSON string result.

        Usage::

            adapter = MellonaWeatherAdapter()
            handlers = {"get_weather": adapter.as_dispatcher_entry()}

            async def dispatcher(name, args):
                handler = handlers.get(name)
                if handler is None:
                    return json.dumps({"error": f"Unknown tool: {name}"})
                return await handler(args)
        """
        weather_tool = self._get_weather_tool()

        # Mellona's as_dispatcher_entry() returns exactly what we need:
        # an async callable (args: dict) -> str that handles all the details.
        return weather_tool.as_dispatcher_entry()
