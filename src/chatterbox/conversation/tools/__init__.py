"""
Built-in tools for the Chatterbox agentic loop.

Each tool module exposes:
- A tool class with an async callable implementation.
- A ``TOOL_DEFINITION`` attribute (``ToolDefinition``) for registering the
  tool with the ``AgenticLoop``.

Usage example::

    from chatterbox.conversation.tools.weather import WeatherTool

    weather = WeatherTool()
    result = await weather.get_weather("Kansas City")
"""

from chatterbox.conversation.tools.weather import WeatherTool

__all__ = ["WeatherTool"]
