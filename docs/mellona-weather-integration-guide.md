# Mellona Weather Tool Integration Guide

This guide demonstrates how to integrate Mellona's weather tool with Chatterbox's persistence and agentic loop framework.

## Overview

The Mellona package provides a high-quality weather tool that queries the Open-Meteo API (free, no API key required). Chatterbox includes an adapter (`MellonaWeatherAdapter`) that seamlessly bridges Mellona's `WeatherTool` to Chatterbox's tool registry and dispatcher interfaces.

### What You'll Get

- Real-time weather data for any location
- Temperature in both Celsius and Fahrenheit
- Humidity, wind speed, and weather conditions
- Full persistence of weather queries in conversation history
- Multi-turn conversations with context preservation

## Quick Start

### 1. Install Mellona

```bash
pip install mellona
```

### 2. Create a Weather-Enabled Conversation

```python
import asyncio
from chatterbox.conversation.tools.mellona_weather import MellonaWeatherAdapter
from chatterbox.conversation.tools.registry import ToolRegistry
from chatterbox.conversation.loop import AgenticLoop
from chatterbox.conversation.providers import OpenAICompatibleProvider
from chatterbox.persistence.backends.sqlite import SQLiteStorage
from chatterbox.persistence.conversation_manager import ConversationManager

async def main():
    # Setup storage
    storage = SQLiteStorage(database_url="sqlite+aiosqlite:///weather_chat.db")
    await storage.initialize()
    await storage.create_tables()

    manager = ConversationManager(storage)
    await manager.initialize()

    # Setup weather tool
    registry = ToolRegistry()

    weather_adapter = MellonaWeatherAdapter(timeout=10.0)
    registry.register(
        weather_adapter.tool_definition,
        weather_adapter.as_dispatcher_entry(),
    )

    # Setup LLM provider (example: OpenAI-compatible)
    provider = OpenAICompatibleProvider(
        base_url="http://localhost:8000/v1",
        api_key="test-key",
        model="llama-2"
    )

    # Create agentic loop with weather tool
    dispatcher = registry.build_dispatcher(timeout=10.0, max_retries=1)
    loop = AgenticLoop(
        provider=provider,
        tool_dispatcher=dispatcher,
    )

    # Create conversation
    conv = await manager.create_conversation(device="voice_assistant")

    # User asks about weather
    user_text = "What's the weather in London?"

    print(f"User: {user_text}")

    # Run the agentic loop
    response = await loop.run(
        user_text=user_text,
        chat_history=[],
        tools=registry.get_definitions(),
    )

    print(f"Assistant: {response}")

    # Store messages in persistent storage
    await manager.store_message(conv.id, "user", user_text)
    await manager.store_message(conv.id, "assistant", response)

    # Get all weather tool calls from conversation
    weather_calls = await manager.get_tool_calls(conv.id, tool_name="get_weather")
    print(f"\nWeather queries in conversation: {len(weather_calls)}")

    for call in weather_calls:
        print(f"- Location: {call.arguments.get('location')}")
        print(f"  Duration: {call.duration_ms}ms")

    await manager.shutdown()

asyncio.run(main())
```

## Complete Multi-Turn Example

Here's a more complete example showing multi-turn weather conversations:

```python
import asyncio
import json
from chatterbox.conversation.tools.mellona_weather import MellonaWeatherAdapter
from chatterbox.conversation.tools.registry import ToolRegistry
from chatterbox.persistence.backends.sqlite import SQLiteStorage
from chatterbox.persistence.conversation_manager import ConversationManager

async def weather_conversation_example():
    """Example: Multi-turn weather conversation with persistence."""

    # Setup
    storage = SQLiteStorage(database_url="sqlite+aiosqlite:///weather_demo.db")
    await storage.initialize()
    await storage.create_tables()

    manager = ConversationManager(storage)
    await manager.initialize()

    # Register weather tool
    registry = ToolRegistry()
    weather_adapter = MellonaWeatherAdapter()
    registry.register(
        weather_adapter.tool_definition,
        weather_adapter.as_dispatcher_entry(),
    )

    # Create conversation
    conv = await manager.create_conversation(
        device="voice_speaker",
        metadata={"user_location": "Boston"}
    )

    # Build dispatcher
    dispatcher = registry.build_dispatcher(timeout=10.0)

    # Simulate conversation turns
    turns = [
        "What's the weather in Paris?",
        "How about London?",
        "Is it warmer in Tokyo?",
    ]

    for user_input in turns:
        print(f"\nUser: {user_input}")

        # Store user message
        await manager.store_message(
            conv.id, "user", user_input,
            metadata={"turn": turns.index(user_input) + 1}
        )

        # Call weather tool directly (in real scenario, LLM would orchestrate)
        # Extract location from user input for this example
        import re
        location_match = re.search(r'in (\w+)', user_input)
        if location_match:
            location = location_match.group(1)

            # Call weather tool
            tool_result = await dispatcher("get_weather", {"location": location})
            weather_data = json.loads(tool_result)

            # Log tool call
            await manager.log_tool_call(
                conversation_id=conv.id,
                call_id=f"call_{turns.index(user_input)}",
                tool_name="get_weather",
                arguments={"location": location},
                result=tool_result,
                duration_ms=500,
                metadata={"api": "open-meteo", "cached": False}
            )

            # Generate response
            if "error" in weather_data:
                response = f"I couldn't find weather for {location}."
            else:
                temp = weather_data["temperature_c"]
                cond = weather_data["conditions"]
                humidity = weather_data["humidity_percent"]
                response = (
                    f"In {weather_data['location_name']}, it's {temp}°C and {cond} "
                    f"with {humidity}% humidity."
                )

            print(f"Assistant: {response}")

            # Store assistant response
            await manager.store_message(
                conv.id, "assistant", response,
                metadata={"used_weather_tool": True}
            )

    # Retrieve full conversation history
    print("\n=== Full Conversation History ===")
    history = await manager.load_history(conv.id)
    for msg in history:
        print(f"[{msg['role'].upper()}]: {msg['content']}")

    # Retrieve all weather queries
    print("\n=== Weather Queries in Conversation ===")
    calls = await manager.get_tool_calls(conv.id, tool_name="get_weather")
    for call in calls:
        location = call.arguments.get("location")
        result = json.loads(call.result)
        if "error" not in result:
            temp = result["temperature_c"]
            print(f"- {location}: {temp}°C ({result['conditions']})")

    # Create context snapshot
    await manager.create_context_snapshot(
        conversation_id=conv.id,
        context_window=history,
        metadata={"reason": "end_of_session", "message_count": len(history)}
    )

    await manager.shutdown()

# Run the example
asyncio.run(weather_conversation_example())
```

## Using Weather Tool with ChatterboxConversationEntity

For integration with the Epic 4 conversation entity:

```python
from chatterbox.conversation.entity import ChatterboxConversationEntity
from chatterbox.conversation.tools.mellona_weather import MellonaWeatherAdapter
from chatterbox.conversation.tools.registry import ToolRegistry
from chatterbox.persistence.conversation_manager import ConversationManager

async def setup_weather_assistant():
    """Setup a voice assistant with weather capabilities and persistence."""

    # Setup storage and manager
    storage = SQLiteStorage(database_url="sqlite+aiosqlite:///voice_assistant.db")
    await storage.initialize()
    await storage.create_tables()

    manager = ConversationManager(storage)
    await manager.initialize()

    # Register tools
    registry = ToolRegistry()

    # Add weather tool
    weather_adapter = MellonaWeatherAdapter()
    registry.register(
        weather_adapter.tool_definition,
        weather_adapter.as_dispatcher_entry(),
    )

    # Build dispatcher with timeout and retry
    dispatcher = registry.build_dispatcher(
        timeout=10.0,
        max_retries=1,
        retry_exceptions=(asyncio.TimeoutError,)
    )

    # Setup LLM provider
    provider = OpenAICompatibleProvider(...)

    # Create conversation entity
    entity = ChatterboxConversationEntity(
        provider=provider,
        tool_dispatcher=dispatcher,
        tools=registry.get_definitions(),
        max_history_turns=20,
        auto_create_conversation_id=True,
    )

    return entity, manager

async def handle_voice_input(entity, manager, voice_text):
    """Handle a voice input and store in database."""
    from chatterbox.conversation.entity import ConversationInput

    # Process through entity
    input_data = ConversationInput(
        text=voice_text,
        conversation_id=None,  # Will be auto-created
        language="en"
    )

    result = await entity.async_process(input_data)

    # Store in database
    conv = await manager.load_conversation(result.conversation_id)
    if not conv:
        # Create new conversation if needed
        conv = await manager.create_conversation(
            conversation_id=result.conversation_id,
            language="en"
        )

    # Store messages
    await manager.store_message(
        conv.id, "user", voice_text
    )
    await manager.store_message(
        conv.id, "assistant", result.response_text,
        metadata=result.extra
    )

    return result
```

## Error Handling

The weather tool handles errors gracefully:

```python
dispatcher = registry.build_dispatcher(timeout=10.0)

# Invalid location
result = await dispatcher("get_weather", {"location": "InvalidCityXYZ"})
data = json.loads(result)
# data = {"error": "Location not found: 'InvalidCityXYZ'"}

# Missing location
result = await dispatcher("get_weather", {})
data = json.loads(result)
# data = {"error": "Missing required argument: location"}

# Timeout
result = await dispatcher("get_weather", {"location": "VeryFarAwayCity"})
# Will retry if configured, then return error if all retries fail
```

## Performance Optimization

### Caching Weather Results

Weather data is relatively static (updates hourly), so you might want to cache:

```python
from chatterbox.persistence.tools.cache import CachingDispatcher
import time

dispatcher = registry.build_dispatcher(timeout=10.0)

# Wrap with caching (TTL in seconds)
cached_dispatcher = CachingDispatcher(
    dispatcher=dispatcher,
    ttl_seconds=3600,  # Cache for 1 hour
)

# First call - hits API
result1 = await cached_dispatcher("get_weather", {"location": "London"})

# Second call - returns cached result
result2 = await cached_dispatcher("get_weather", {"location": "London"})
```

### Limiting API Calls

Use the rate limiter to avoid overwhelming the Open-Meteo API:

```python
from chatterbox.persistence.tools.registry import ToolRegistry

registry = ToolRegistry()
weather_adapter = MellonaWeatherAdapter()
registry.register(
    weather_adapter.tool_definition,
    weather_adapter.as_dispatcher_entry(),
)

# Build with timeout and retry settings
dispatcher = registry.build_dispatcher(
    timeout=10.0,
    max_retries=2,
)
```

## Troubleshooting

### "ImportError: No module named 'mellona'"

**Solution:** Install mellona package

```bash
pip install mellona
```

### Weather Tool Times Out

**Solution:** Increase timeout or check internet connection

```python
# Increase timeout to 20 seconds
dispatcher = registry.build_dispatcher(timeout=20.0)

# Also increase in adapter
adapter = MellonaWeatherAdapter(timeout=20.0)
```

### Same Weather Result Returned Multiple Times

**Solution:** Weather data is cached and updated hourly by Open-Meteo. This is expected behavior.

### Location Not Found

**Solution:** Use clear location names recognized by Open-Meteo

```python
# Good
"London"
"Paris, France"
"New York, USA"
"Sydney, Australia"

# Less reliable
"London, UK"  # Use "United Kingdom" or just "London"
"NYC"  # Use "New York"
```

## See Also

- [Persistence API Guide](persistence-api-guide.md) - ConversationManager API reference
- [Mellona Documentation](https://github.com/cackle/mellona) - Mellona project
- [Open-Meteo API](https://open-meteo.com/) - Weather data source
- [Tool Development Guide](tool-development.md) - Creating custom tools
