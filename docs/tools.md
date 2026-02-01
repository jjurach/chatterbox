# Tools and Skills System

The Cackle agent can be extended with tools (also called skills) that allow it to perform actions beyond conversation. This document explains the tool system and how to add custom tools.

## Understanding Tools

A tool is a function that the agent can invoke to perform a specific action. The agent learns to use tools based on their description and the context of the conversation.

### Built-in Tools

Currently available tools:

#### GetTime
Gets the current date and time.

**Function:** `cackle.tools.builtin.time_tool.get_time()`

**Agent Description:** "Get the current date and time. Use this when the user asks for the time, date, or current moment."

**Example:**
```python
from cackle.tools.builtin import get_time
print(get_time())  # Output: "2024-01-15 14:30:45"
```

**Agent Usage:**
```
User: "What time is it?"
Agent: [Uses GetTime tool]
Agent Response: "It is currently 2024-01-15 14:30:45."
```

## Tool System Architecture

### Tool Registry

The tool registry (`cackle/tools/registry.py`) centralizes tool definition:

```python
from cackle.tools import get_available_tools

tools = get_available_tools()
# Returns list of LangChain Tool objects
```

### Tool Structure

Each tool has:
1. **Name**: Unique identifier (e.g., "GetTime")
2. **Function**: Python callable that performs the action
3. **Description**: Human-readable explanation for the agent

```python
Tool(
    name="GetTime",
    func=get_time,
    description="Get the current date and time. Use this when the user asks for the time, date, or current moment."
)
```

## Adding a Custom Tool

### Step 1: Create Tool Function

Create a new file in `cackle/tools/builtin/`:

```python
# cackle/tools/builtin/weather_tool.py
"""Weather tool for the Cackle agent."""


def get_weather(location: str = "current") -> str:
    """Get weather information for a location.

    Args:
        location: City name or "current" for current location

    Returns:
        Weather information as a string
    """
    # Implement your weather logic here
    # For example, call a weather API
    return f"Weather in {location}: Sunny, 72°F"
```

### Step 2: Export from Builtin

Update `cackle/tools/builtin/__init__.py`:

```python
"""Built-in tools for the Cackle agent."""

from cackle.tools.builtin.time_tool import get_time
from cackle.tools.builtin.weather_tool import get_weather

__all__ = ["get_time", "get_weather"]
```

### Step 3: Register the Tool

Update `cackle/tools/registry.py`:

```python
from cackle.tools.builtin.weather_tool import get_weather

def get_available_tools() -> List[Tool]:
    """Get the list of available tools for the agent."""
    tools = [
        Tool(
            name="GetTime",
            func=get_time,
            description="Get the current date and time. Use this when the user asks for the time, date, or current moment.",
        ),
        Tool(
            name="GetWeather",
            func=get_weather,
            description="Get current weather information. Use this when the user asks about the weather.",
        ),
    ]
    return tools
```

### Step 4: Write Tests

Create `tests/core/test_weather_tool.py`:

```python
"""Tests for the weather tool."""

from cackle.tools.builtin import get_weather


def test_get_weather():
    """Test the get_weather tool function."""
    result = get_weather("New York")
    assert isinstance(result, str)
    assert "weather" in result.lower()
```

### Step 5: Test with Agent

```python
from cackle.agent import VoiceAssistantAgent

agent = VoiceAssistantAgent()
response = await agent.process_input("What's the weather in New York?")
# Agent will use the GetWeather tool
```

## Tool Best Practices

### 1. Clear Descriptions

The agent uses the description to decide when to use a tool. Make it clear and specific:

```python
# Good
description="Get current weather information for a location. Use when user asks about weather, temperature, or conditions."

# Bad
description="Weather function"
```

### 2. Simple Interfaces

Keep tool functions simple with minimal parameters:

```python
# Good
def get_weather(location: str) -> str:
    pass

# Bad
def get_weather(location: str, units: str, include_forecast: bool, days: int) -> dict:
    pass
```

### 3. Handle Errors Gracefully

Return user-friendly error messages:

```python
def get_weather(location: str) -> str:
    try:
        # Fetch weather data
        return weather_info
    except Exception as e:
        return f"I couldn't get weather for {location}. Please try again."
```

### 4. Return Strings

Always return strings for agent compatibility:

```python
# Good
return "Sunny, 72°F"

# Bad
return {"condition": "sunny", "temp": 72}
```

### 5. Document Tool Purpose

Include clear docstrings:

```python
def get_stock_price(symbol: str) -> str:
    """Get current stock price for a symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        Current stock price information as a formatted string

    Example:
        >>> get_stock_price("AAPL")
        "Apple Inc (AAPL) is trading at $175.43"
    """
    pass
```

## Advanced Topics

### Tools with External APIs

```python
import httpx

async def get_news(topic: str) -> str:
    """Get latest news for a topic."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://newsapi.org/v2/everything?q={topic}")
        articles = response.json()["articles"][:3]
        return "\n".join([a["title"] for a in articles])
```

### Tools with State

```python
class TodoTool:
    def __init__(self):
        self.todos = []

    def add_todo(self, task: str) -> str:
        self.todos.append(task)
        return f"Added: {task}"

    def list_todos(self) -> str:
        return "\n".join(self.todos)
```

### Conditional Tool Registration

```python
def get_available_tools() -> List[Tool]:
    tools = [get_time_tool()]

    if settings.enable_weather:
        tools.append(get_weather_tool())

    if settings.enable_news:
        tools.append(get_news_tool())

    return tools
```

## Troubleshooting

### Agent Not Using Tool
- Check tool description is clear
- Verify tool function returns string
- Ensure tool is registered in registry
- Enable debug mode to see agent reasoning

### Tool Function Errors
- Add error handling to function
- Test tool independently before adding
- Log errors for debugging
- Return user-friendly error messages

### Tool Takes Too Long
- Optimize underlying function
- Add timeout handling
- Consider async implementation
- Cache results if appropriate

## Tool Ideas

Consider implementing these tools:

- **GetNews**: Fetch latest news articles
- **GetWeather**: Current weather and forecast
- **GetPrice**: Stock prices or product prices
- **SearchWeb**: Web search functionality
- **SendEmail**: Email notifications
- **GetTransit**: Public transportation info
- **CalendarEvent**: Create or check calendar events
- **TodoList**: Manage todos
- **Calculator**: Complex math operations
- **Translate**: Language translation

## Contributing Tools

To contribute a tool:

1. Implement following best practices above
2. Write comprehensive tests
3. Document with clear examples
4. Submit PR with feature branch: `tools/tool-name`
5. Ensure all tests pass: `pytest tests/core/test_tools.py`

---
Last Updated: 2026-02-01
