# Persistence API Guide: ConversationManager

This guide documents the ConversationManager API for persisting conversations, messages, tool calls, and context snapshots to durable storage.

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [API Reference](#api-reference)
4. [Usage Examples](#usage-examples)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)

## Overview

The `ConversationManager` bridges Epic 4 (LLM framework) and Epic 5 (persistent storage), enabling:

- **Conversation Persistence**: Store and retrieve multi-turn conversations
- **Tool Call Logging**: Log all tool invocations with arguments, results, and execution time
- **Token Tracking**: Track token usage for cost analysis
- **Context Snapshots**: Capture conversation state for debugging and replay
- **User Isolation**: Ensure conversations are properly segregated per user

### Architecture

```
ChatterboxConversationEntity (Epic 4)
         ↓
   AgenticLoop (runs conversation)
         ↓
ConversationManager (this API)
         ↓
StorageBackend (SQLite, PostgreSQL, etc.)
         ↓
Database
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install chatterbox[persistence]
```

### 2. Initialize Storage

```python
import asyncio
from chatterbox.persistence.backends.sqlite import SQLiteStorage
from chatterbox.persistence.conversation_manager import ConversationManager

async def main():
    # Create storage backend
    storage = SQLiteStorage(
        database_url="sqlite+aiosqlite:///chatterbox.db"
    )

    # Initialize
    await storage.initialize()
    await storage.create_tables()

    # Create manager
    manager = ConversationManager(storage)
    await manager.initialize()

    # Use the manager...

    # Cleanup
    await manager.shutdown()

asyncio.run(main())
```

### 3. Database Location

By default, SQLite creates `chatterbox.db` in the current directory.

For production, use PostgreSQL:

```python
storage = SQLiteStorage(
    database_url="postgresql+asyncpg://user:password@localhost/chatterbox"
)
```

## API Reference

### ConversationManager

The main class for persistence operations.

#### Initialization

```python
manager = ConversationManager(storage: StorageBackend)
```

**Parameters:**
- `storage`: A StorageBackend implementation (SQLiteStorage, PostgreSQL backend, etc.)

#### Methods

##### `async initialize() → None`

Initialize the storage backend. Must be called before any other operations.

```python
await manager.initialize()
```

**Raises:** Exception if initialization fails

---

##### `async shutdown() → None`

Shut down the storage backend gracefully. Safe to call multiple times.

```python
await manager.shutdown()
```

---

##### `async load_history(conversation_id: str, limit: int | None = None) → list[dict]`

Load conversation history for context.

```python
history = await manager.load_history(conv_id, limit=20)
# Returns: [{"role": "user", "content": "..."}, ...]
```

**Parameters:**
- `conversation_id`: The conversation's UUID
- `limit`: Maximum number of recent messages (None = all)

**Returns:** List of message dicts with "role" and "content" keys

**Example:**
```python
# Load full history
history = await manager.load_history(conv_id)

# Load last 10 messages
recent = await manager.load_history(conv_id, limit=10)
```

---

##### `async create_conversation(...) → Conversation`

Create a new conversation record.

```python
conv = await manager.create_conversation(
    user_id="user_123",
    language="en",
    device="living_room",
    metadata={"timezone": "UTC"}
)
```

**Parameters:**
- `user_id`: Optional user ID
- `conversation_id`: Optional UUID (auto-generated if omitted)
- `language`: BCP-47 language tag (default: "en")
- `device`: Optional device identifier
- `metadata`: Optional JSON metadata dict

**Returns:** Conversation object with id, conversation_id, etc.

---

##### `async load_conversation(conversation_id: str) → Conversation | None`

Load a conversation record.

```python
conv = await manager.load_conversation(conv_id)
if conv is None:
    print("Conversation not found")
```

**Parameters:**
- `conversation_id`: The conversation's UUID

**Returns:** Conversation object, or None if not found

---

##### `async store_message(...) → Message`

Store a message in the conversation.

```python
msg = await manager.store_message(
    conversation_id=conv_id,
    role="user",
    content="What's the weather?",
    metadata={"input_tokens": 10}
)
```

**Parameters:**
- `conversation_id`: FK to Conversation.id
- `role`: "user", "assistant", or "system"
- `content`: The message text
- `metadata`: Optional JSON metadata (token count, latency, etc.)

**Returns:** Message object with sequence number, timestamps, etc.

**Valid Roles:**
- `"user"`: User input
- `"assistant"`: LLM response
- `"system"`: System prompts or instructions

**Example:**
```python
# Store user message
await manager.store_message(conv_id, "user", "Tell me about Python")

# Store assistant response with token info
await manager.store_message(
    conv_id,
    "assistant",
    "Python is a programming language...",
    metadata={"output_tokens": 150, "model": "gpt-4"}
)
```

---

##### `async log_tool_call(...) → ToolCall`

Log a tool invocation.

```python
tool_call = await manager.log_tool_call(
    conversation_id=conv_id,
    call_id="call_123",
    tool_name="get_weather",
    arguments={"location": "London"},
    result='{"temperature": 15, "conditions": "Rainy"}',
    duration_ms=500,
    metadata={"api": "open-meteo"}
)
```

**Parameters:**
- `conversation_id`: FK to Conversation.id
- `call_id`: Tool call ID from LLM
- `tool_name`: Name of the tool (e.g., "get_weather")
- `arguments`: JSON dict of input arguments
- `message_id`: Optional FK to Message (message containing tool_calls)
- `result`: Optional result string (typically JSON)
- `error`: Optional error message if failed
- `duration_ms`: Optional execution time in milliseconds
- `metadata`: Optional additional metadata dict

**Returns:** ToolCall object

**Example:**
```python
import time
import json

start = time.time()
weather = await weather_tool.get_weather("London")
duration = int((time.time() - start) * 1000)

await manager.log_tool_call(
    conversation_id=conv_id,
    call_id="call_w1",
    tool_name="get_weather",
    arguments={"location": "London"},
    result=json.dumps(weather),
    duration_ms=duration,
    metadata={"cache_hit": False}
)
```

---

##### `async get_tool_calls(...) → list[ToolCall]`

Retrieve tool calls from a conversation.

```python
# Get all tool calls
calls = await manager.get_tool_calls(conv_id)

# Get only weather tool calls
weather_calls = await manager.get_tool_calls(conv_id, tool_name="get_weather")
```

**Parameters:**
- `conversation_id`: FK to Conversation.id
- `tool_name`: Optional filter by tool name
- `limit`: Maximum results (default: 100)

**Returns:** List of ToolCall objects

---

##### `async create_context_snapshot(...) → ContextSnapshot`

Create a context snapshot for debugging.

```python
snapshot = await manager.create_context_snapshot(
    conversation_id=conv_id,
    context_window=history,
    message_sequence=42,
    metadata={"reason": "truncation"}
)
```

**Parameters:**
- `conversation_id`: FK to Conversation.id
- `context_window`: List of message dicts in the context
- `message_sequence`: Optional message sequence number
- `metadata`: Optional metadata dict (reason, counts, etc.)

**Returns:** ContextSnapshot object

---

##### `async healthcheck() → bool`

Check if storage backend is healthy.

```python
is_healthy = await manager.healthcheck()
if not is_healthy:
    print("Storage backend is unavailable")
```

**Returns:** True if backend is healthy, False otherwise

## Usage Examples

### Example 1: Basic Multi-Turn Conversation

```python
import asyncio
from chatterbox.persistence.backends.sqlite import SQLiteStorage
from chatterbox.persistence.conversation_manager import ConversationManager

async def main():
    # Setup
    storage = SQLiteStorage(database_url="sqlite+aiosqlite:///chat.db")
    await storage.initialize()
    await storage.create_tables()

    manager = ConversationManager(storage)
    await manager.initialize()

    try:
        # Create conversation
        conv = await manager.create_conversation(
            user_id="alice",
            device="phone"
        )
        print(f"Created conversation: {conv.conversation_id}")

        # Turn 1
        await manager.store_message(conv.id, "user", "What's the capital of France?")
        await manager.store_message(conv.id, "assistant", "The capital of France is Paris.")

        # Turn 2
        await manager.store_message(conv.id, "user", "What's its population?")
        await manager.store_message(conv.id, "assistant", "Paris has approximately 2.2 million people.")

        # Load and display history
        history = await manager.load_history(conv.id)
        for i, msg in enumerate(history):
            print(f"[{i}] {msg['role']}: {msg['content']}")

    finally:
        await manager.shutdown()

asyncio.run(main())
```

### Example 2: Weather Conversation with Tool Calls

```python
async def weather_conversation():
    # ... setup manager ...

    conv = await manager.create_conversation(device="voice_assistant")

    # User asks about weather
    await manager.store_message(
        conv.id, "user",
        "What's the weather in London?",
        metadata={"source": "voice"}
    )

    # Tool call: get weather
    result = await weather_tool.get_weather("London")
    await manager.log_tool_call(
        conv.id,
        call_id="call_1",
        tool_name="get_weather",
        arguments={"location": "London"},
        result=json.dumps(result),
        duration_ms=850
    )

    # Assistant responds
    await manager.store_message(
        conv.id, "assistant",
        f"It's {result['temperature_c']}°C and {result['conditions']} in London.",
        metadata={"used_tool": True}
    )

    # Load conversation for context
    history = await manager.load_history(conv.id)
    return history
```

### Example 3: Context Snapshots for Debugging

```python
async def snapshot_example():
    # ... setup manager ...

    conv = await manager.create_conversation()

    # ... store many messages ...

    for i in range(100):
        await manager.store_message(
            conv.id, "user" if i % 2 == 0 else "assistant",
            f"Message {i}"
        )

    # Load context
    history = await manager.load_history(conv.id, limit=20)

    # Create snapshot before truncation
    await manager.create_context_snapshot(
        conversation_id=conv.id,
        context_window=history,
        metadata={
            "reason": "before_truncation",
            "original_count": 100,
            "kept_count": 20
        }
    )
```

## Configuration

### SQLite Options

```python
storage = SQLiteStorage(
    database_url="sqlite+aiosqlite:///chatterbox.db",
    echo=False,  # Log SQL statements
    connect_args={"timeout": 30}  # Connection timeout
)
```

### Environment Variables

Set database location via environment:

```bash
export CHATTERBOX_DB="sqlite+aiosqlite:////tmp/chatterbox.db"
```

## Troubleshooting

### "Storage backend not initialized" Error

**Problem:** Getting RuntimeError when trying to use manager

**Solution:** Call `await manager.initialize()` after creating the manager

```python
manager = ConversationManager(storage)
await manager.initialize()  # Don't forget this!
```

### "no such table" Error

**Problem:** SQLAlchemy complaining about missing tables

**Solution:** Call `await storage.create_tables()` after initialization

```python
await storage.initialize()
await storage.create_tables()  # Create schema
```

### Database is Locked

**Problem:** SQLite database file is locked (especially on networked storage)

**Solution:** Use PostgreSQL for multi-process scenarios

```python
# PostgreSQL instead of SQLite
storage = SQLiteStorage(
    database_url="postgresql+asyncpg://user:pass@localhost/chatterbox"
)
```

### Performance Issues with Large Conversations

**Problem:** Loading history for conversations with thousands of messages is slow

**Solution:** Use the `limit` parameter to load only recent messages

```python
# Good: Load only last 50 messages
recent = await manager.load_history(conv_id, limit=50)

# Bad: Load all 10,000 messages
all_msgs = await manager.load_history(conv_id)
```

### Metadata Not Persisting

**Problem:** Metadata dict appears empty after retrieval

**Solution:** Metadata is preserved in the database. Reload from database if needed

```python
# Store with metadata
msg = await manager.store_message(
    conv_id, "user", "Test",
    metadata={"key": "value"}
)

# Metadata is in the database, reload to verify
from sqlalchemy import select
async with storage.get_session() as session:
    result = await session.execute(
        select(Message).where(Message.id == msg.id)
    )
    reloaded = result.scalars().first()
    # reloaded.message_metadata contains the persisted metadata
```

## See Also

- [Persistent Storage Architecture](persistent-storage-architecture.md) - Design decisions
- [Context Retrieval Guide](context-retrieval-guide.md) - Loading and managing context
- [Epic 4 Conversation Framework](agentic-loop.md) - LLM integration details
