"""
Agent tools for the Voice Assistant.

This module defines the tools available to the LangChain agent for processing
user queries and performing actions.
"""

from datetime import datetime
from typing import List

from langchain_classic.agents import Tool


def get_time() -> str:
    """Get the current time and date.

    Returns:
        A formatted string with the current date and time (YYYY-MM-DD HH:MM:SS)
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_available_tools() -> List[Tool]:
    """Get the list of available tools for the agent.

    This function centralizes tool definition, making it easy to add new tools
    in the future. Each tool requires:
    - name: Unique identifier for the tool
    - func: Callable that performs the tool's action
    - description: What the tool does (used by LLM to decide when to use it)

    Returns:
        A list of Tool objects available to the agent

    Example:
        To add a new tool, define a function and add it to the list:

        def get_weather(location: str) -> str:
            '''Get weather for a location.'''
            # implementation here
            return "Sunny, 72°F"

        Then add to the tools list:
        Tool(
            name="GetWeather",
            func=lambda location: get_weather(location),
            description="Get current weather for a location"
        )
    """
    tools = [
        Tool(
            name="GetTime",
            func=get_time,
            description="Get the current date and time. Use this when the user asks for the time, date, or current moment.",
        ),
    ]

    return tools
