# Protocol Adapters

Adapters provide protocol-specific implementations that integrate the core Cackle agent with different systems. This document explains how adapters work and how to create custom adapters.

## Available Adapters

### Wyoming Adapter

The Wyoming adapter implements the Wyoming protocol for communication with ESP32 voice devices.

**Location:** `cackle/adapters/wyoming/`

**Components:**
- `server.py` - Wyoming protocol server implementation
- `client.py` - Test client for development and debugging

**Audio Format Specification**

The Wyoming protocol uses raw PCM audio streaming with the following standard configuration:
- **Sampling rate**: 16000 Hz
- **Channels**: 1 (mono)
- **Format**: S16_LE (signed 16-bit little endian)
- **Payload chunks**: 2048-3200 bytes per message
- **Protocol structure**: Newline-delimited JSON headers with binary PCM payload

This is the audio format you should configure in your ESPHome firmware when flashing ESP32 devices.

**Usage:**

```python
from cackle.adapters.wyoming import VoiceAssistantServer

server = VoiceAssistantServer(
    host="0.0.0.0",
    port=10700,
    ollama_base_url="http://localhost:11434/v1",
    ollama_model="llama3.1:8b"
)

import asyncio
asyncio.run(server.run())
```

**Command Line:**
```bash
chatterbox3b-server
chatterbox3b-server --debug
python examples/wyoming_server.py
```

## Adapter Architecture

Adapters follow a consistent pattern:

```
cackle/adapters/
├── protocol/
│   ├── __init__.py          # Public API
│   ├── server.py            # Protocol server implementation
│   └── client.py            # Test/dev client (if applicable)
└── (other protocols...)
```

### Server Implementation

Each adapter server:
1. Receives protocol-specific events
2. Converts to agent input
3. Processes through `VoiceAssistantAgent`
4. Returns protocol-specific responses

### Integration Points

The Wyoming server integrates with the agent through:
- **Initialization**: Creates `VoiceAssistantAgent` instance
- **Event Handling**: Processes Wyoming events
- **Tool Access**: Uses agent's tools through agent interface
- **Response Format**: Converts agent output to Wyoming events

## Creating a Custom Adapter

### Step 1: Create Adapter Directory

```bash
mkdir -p cackle/adapters/myprotocol
touch cackle/adapters/myprotocol/__init__.py
touch cackle/adapters/myprotocol/server.py
```

### Step 2: Implement Server Class

```python
# cackle/adapters/myprotocol/server.py

from cackle.agent import VoiceAssistantAgent

class MyProtocolServer:
    """Server implementation for MyProtocol."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9000,
        **agent_kwargs
    ):
        """Initialize the server with agent configuration."""
        self.host = host
        self.port = port
        self.agent = VoiceAssistantAgent(**agent_kwargs)

    async def run(self):
        """Run the server."""
        # Implement protocol-specific server logic
        pass

    async def handle_input(self, user_input: str) -> str:
        """Process user input through the agent."""
        return await self.agent.process_input(user_input)
```

### Step 3: Export Public API

```python
# cackle/adapters/myprotocol/__init__.py

"""MyProtocol adapter for Cackle agent."""

from cackle.adapters.myprotocol.server import MyProtocolServer

__all__ = ["MyProtocolServer"]
```

### Step 4: Create Tests

```python
# tests/adapters/myprotocol/test_server.py

from cackle.adapters.myprotocol import MyProtocolServer

def test_server_initialization():
    server = MyProtocolServer()
    assert server is not None
```

### Step 5: Add Documentation

Create `docs/adapters_myprotocol.md` with:
- Protocol overview
- Setup instructions
- Usage examples
- Configuration options

## Best Practices

### 1. Keep Protocol Logic Separate
- All protocol-specific code in adapter
- Use agent through public API only
- Don't patch core agent for adapter needs

### 2. Implement Proper Error Handling
```python
async def handle_input(self, user_input: str) -> str:
    try:
        return await self.agent.process_input(user_input)
    except Exception as e:
        logger.error(f"Error processing input: {e}")
        return "I encountered an error. Please try again."
```

### 3. Support Configuration
```python
from cackle.config import get_settings

class MyProtocolServer:
    def __init__(self, **kwargs):
        settings = get_settings()
        self.host = kwargs.get("host", settings.host)
        self.port = kwargs.get("port", settings.port)
```

### 4. Provide Test Clients
Include test/debug clients for development:
```python
# cackle/adapters/myprotocol/client.py
async def send_test_message(text: str, host: str, port: int):
    """Send a test message to the server."""
    pass
```

### 5. Document Protocol Specifics
Explain how protocol features map to agent capabilities:
- Input format conversion
- Output format conversion
- Special protocol features
- Limitations and workarounds

## Adapter Examples

### HTTP/REST Adapter (Future)

```python
from fastapi import FastAPI
from cackle.agent import VoiceAssistantAgent

app = FastAPI()

@app.post("/chat")
async def chat(message: str):
    agent = VoiceAssistantAgent()
    response = await agent.process_input(message)
    return {"response": response}
```

### WebSocket Adapter (Future)

```python
import websockets
from cackle.agent import VoiceAssistantAgent

async def handle_connection(websocket):
    agent = VoiceAssistantAgent()
    async for message in websocket:
        response = await agent.process_input(message)
        await websocket.send(response)
```

## Contributing Adapters

To contribute a new adapter:

1. Implement following the patterns above
2. Include comprehensive tests
3. Write documentation with examples
4. Submit PR with feature branch: `adapters/protocol-name`
5. Ensure all tests pass: `pytest tests/adapters/`

## Protocol Comparison

| Adapter | Use Case | Status |
|---------|----------|--------|
| Wyoming | ESP32 voice devices | Implemented |
| HTTP/REST | Web applications | Planned |
| WebSocket | Real-time web clients | Planned |
| UART | Direct serial communication | Future |
| MQTT | IoT systems | Future |

## Troubleshooting

### Server Won't Start
- Check port availability: `lsof -i :PORT`
- Verify bind address is accessible
- Check logs with debug flag

### Agent Not Responding
- Ensure Ollama is running
- Verify agent configuration
- Check network connectivity to Ollama

### Protocol Events Not Received
- Verify protocol format is correct
- Check network connectivity
- Enable debug logging in adapter
