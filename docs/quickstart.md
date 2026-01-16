# Cackle Agent - Quick Start Guide

## Installation

Prerequisites:
- Python 3.10+
- Ollama running with llama3.1:8b model

Install the package:
```bash
pip install -e .
```

## Using the Agent Directly

The simplest way to use Cackle is with the core agent directly:

```python
import asyncio
from cackle.agent import VoiceAssistantAgent

async def main():
    agent = VoiceAssistantAgent(
        ollama_base_url="http://localhost:11434/v1",
        ollama_model="llama3.1:8b"
    )

    response = await agent.process_input("What time is it?")
    print(response)

asyncio.run(main())
```

Or run the example:
```bash
python examples/direct_agent.py
```

## Running the Wyoming Server

To run the agent as a Wyoming protocol server for ESP32 devices:

```bash
chatterbox3b-server
```

Or with debug logging:
```bash
chatterbox3b-server --debug
```

Or run the example:
```bash
python examples/wyoming_server.py --debug
```

The server will bind to `0.0.0.0:10700` and accept Wyoming protocol connections from ESP32 devices. The server validates Ollama connectivity before starting and displays the bound address in logs.

## Testing the Wyoming Server

### Local Testing

Once the server is running, test it with the Wyoming client from the same machine:

```bash
python examples/wyoming_client_test.py "What time is it?"
```

Or use the installed command:
```bash
chatterbox3b-wyoming-client "Hello"
```

### Network Testing

To test from another device on your network (e.g., before flashing an ESP32), get your server's local IP and test from another machine:

```bash
# From another device on the same network
python examples/wyoming_client_test.py "Hello" --host 192.168.0.X
```

Replace `192.168.0.X` with your server's actual IP address on your local network.

### Wyoming Protocol Audio Format

When flashing ESP32 devices with ESPHome firmware, configure them to send audio in the Wyoming protocol's standard format:

- **Sampling rate**: 16000 Hz
- **Channels**: 1 (mono)
- **Bit depth**: 16-bit signed (S16_LE)
- **Payload chunks**: 2048-3200 bytes

The server will automatically handle this format and route the audio through the agent for processing.

## Configuration

Configure the agent via environment variables:

```bash
# Ollama settings
export OLLAMA_BASE_URL="http://localhost:11434/v1"
export OLLAMA_MODEL="llama3.1:8b"
export OLLAMA_TEMPERATURE=0.7

# Server settings
export HOST="0.0.0.0"
export PORT=10700

# Agent settings
export CONVERSATION_WINDOW_SIZE=3

# Logging
export LOG_LEVEL="INFO"
```

## Basic Examples

### Example 1: Simple Query
```python
agent = VoiceAssistantAgent()
response = await agent.process_input("What is 2+2?")
print(response)
```

### Example 2: Conversation with Memory
```python
agent = VoiceAssistantAgent(conversation_window_size=5)

# First message
response1 = await agent.process_input("My name is Alice")
print(response1)

# Agent remembers context
response2 = await agent.process_input("What's my name?")
print(response2)  # Should reference "Alice"
```

### Example 3: Using Tools
The agent automatically has access to tools:
```python
response = await agent.process_input("What time is it?")
# Agent will use the GetTime tool and return the current time
```

### Example 4: Debug Mode
Enable detailed logging:
```python
agent = VoiceAssistantAgent(debug=True)
response = await agent.process_input("Hello")
# See detailed LangChain execution logs
```

## Common Tasks

### Reset Conversation Memory
```python
agent.reset_memory()
```

### Get Memory Summary
```python
summary = agent.get_memory_summary()
print(summary)
```

### Change Models Dynamically
Create a new agent with different settings:
```python
faster_agent = VoiceAssistantAgent(
    ollama_model="phi:latest",
    ollama_temperature=0.5
)
```

## Troubleshooting

**Connection Error to Ollama**
- Ensure Ollama is running: `ollama serve`
- Check Ollama URL matches: `OLLAMA_BASE_URL="http://localhost:11434/v1"`
- Test Ollama directly: `curl http://localhost:11434/api/tags`

**Wyoming Server Won't Start**
- Check port isn't in use: `lsof -i :10700`
- Ensure proper permissions for binding to host/port
- Check logs with `--debug` flag

**Agent Responses Are Slow**
- Use a faster model: `OLLAMA_MODEL="phi:latest"`
- Reduce conversation window: `CONVERSATION_WINDOW_SIZE=2`
- Reduce temperature for faster responses: `OLLAMA_TEMPERATURE=0.3`

## Next Steps

- Read [Architecture Documentation](architecture.md) to understand the design
- Explore [Adding Tools](tools.md) to extend capabilities
- Check [Adapter Documentation](adapters.md) for custom protocol support
- Review [Examples](../examples/) for more use cases

## Getting Help

For issues and feature requests, see the project repository.
