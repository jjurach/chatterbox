"""
Built-in tools for the Chatterbox agentic loop.

Each tool module exposes:
- A tool class with an async callable implementation.
- A ``TOOL_DEFINITION`` attribute (``ToolDefinition``) for registering the
  tool with the ``AgenticLoop``.
- An ``as_dispatcher_entry()`` method returning a handler for ``ToolRegistry``.

The ``ToolRegistry`` class manages tool registration and produces a dispatcher
callable (with timeout and retry support) for use with ``AgenticLoop``.

Quick-start example::

    from chatterbox.conversation.tools import ToolRegistry, WeatherTool, DateTimeTool

    registry = ToolRegistry()
    weather = WeatherTool()
    registry.register(WeatherTool.TOOL_DEFINITION, weather.as_dispatcher_entry())

    dt = DateTimeTool()
    registry.register(DateTimeTool.TOOL_DEFINITION, dt.as_dispatcher_entry())

    dispatcher = registry.build_dispatcher(timeout=10.0, max_retries=1)
"""

from chatterbox.conversation.tools.datetime_tool import DateTimeTool
from chatterbox.conversation.tools.registry import AsyncToolHandler, ToolRegistry
from chatterbox.conversation.tools.weather import WeatherTool

__all__ = ["AsyncToolHandler", "DateTimeTool", "ToolRegistry", "WeatherTool"]
