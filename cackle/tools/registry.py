"""
Tool registry for the Cackle agent.

This module provides a centralized registry of available tools that can be
used by the agent. Tools can be built-in or custom.
"""

from typing import List
from langchain_classic.agents import Tool
from cackle.tools.builtin.time_tool import get_time
from cackle.tools.builtin.stt_tool import STTTool
from cackle.tools.builtin.tts_tool import TTSTool


def get_available_tools() -> List[Tool]:
    """Get the list of available tools for the agent.

    This function centralizes tool definition, making it easy to add new tools.

    Returns:
        A list of Tool objects available to the agent
    """
    tools = [
        Tool(
            name="GetTime",
            func=get_time,
            description="Get the current date and time. Use this when the user asks for the time, date, or current moment.",
        ),
        STTTool(),
        TTSTool(),
    ]

    return tools
