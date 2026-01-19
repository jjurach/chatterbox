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

### Full Voice Assistant (Default)

To run the agent as a Wyoming protocol server for ESP32 devices:

```bash
chatterbox-server
```

Or with debug logging:
```bash
chatterbox-server --debug
```

The server will bind to `0.0.0.0:10700` and accept Wyoming protocol connections from ESP32 devices.

### STT-Only Server (Whisper Transcription)

Run a dedicated speech-to-text service:

```bash
chatterbox-server --mode stt_only
```

### TTS-Only Server (Piper Synthesis)

Run a dedicated text-to-speech service:

```bash
chatterbox-server --mode tts_only
```

### Combined Mode (STT + TTS without Agent)

Run STT and TTS services without the full voice assistant:

```bash
chatterbox-server --mode combined
```

### Enable REST API

Run the Wyoming server with a REST API endpoint:

```bash
chatterbox-server --rest --rest-port 8080
```

This enables both Wyoming protocol and REST API on separate ports.

## Testing the Wyoming Server

### Local Testing

Once the server is running, test it with the Wyoming client from the same machine:

```bash
python examples/wyoming_client_test.py "What time is it?"
```

Or use the installed command:
```bash
chatterbox-wyoming-client "Hello"
```

### Network Testing

To test from another device on your network (e.g., before flashing an ESP32), get your server's local IP and test from another machine:

```bash
# From another device on the same network
python examples/wyoming_client_test.py "Hello" --host 192.168.0.X
```

Replace `192.168.0.X` with your server's actual IP address on your local network.

### Wyoming Protocol Integration

ESPHome firmware communicates with Home Assistant using its native protocols. Home Assistant then connects to Chatterbox3b services (STT with Whisper, TTS with Piper) using the Wyoming protocol.

When configuring ESPHome devices, ensure they are set up to work with Home Assistant's voice assistant integration. Home Assistant handles the audio format conversion and protocol translation between ESPHome and Wyoming.

The Wyoming protocol uses the following standard audio format for communication between Home Assistant and Chatterbox3b services:

- **Sampling rate**: 16000 Hz
- **Channels**: 1 (mono)
- **Bit depth**: 16-bit signed (S16_LE)
- **Payload chunks**: 2048-3200 bytes

## Configuration

Configure the server via environment variables:

```bash
# Server mode: full, stt_only, tts_only, combined
export CHATTERBOX_SERVER_MODE=full

# Ollama settings (required for 'full' and 'combined' modes)
export CHATTERBOX_OLLAMA_BASE_URL="http://localhost:11434/v1"
export CHATTERBOX_OLLAMA_MODEL="llama3.1:8b"
export CHATTERBOX_OLLAMA_TEMPERATURE=0.7

# STT settings (Whisper)
export CHATTERBOX_STT_MODEL=base           # tiny, base, small, medium, large
export CHATTERBOX_STT_DEVICE=cpu           # cpu, cuda
export CHATTERBOX_STT_LANGUAGE=            # Leave empty for auto-detect

# TTS settings (Piper)
export CHATTERBOX_TTS_VOICE=en_US-lessac-medium
export CHATTERBOX_TTS_SAMPLE_RATE=22050

# Wyoming server settings
export CHATTERBOX_HOST="0.0.0.0"
export CHATTERBOX_PORT=10700

# REST API settings
export CHATTERBOX_ENABLE_REST=false
export CHATTERBOX_REST_PORT=8080

# Agent settings
export CHATTERBOX_CONVERSATION_WINDOW_SIZE=3

# Logging
export CHATTERBOX_LOG_LEVEL="INFO"
```

See [STT/TTS Services Guide](stt_tts_services.md) for detailed configuration options.

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

## STT/TTS Services

Chatterbox now includes dedicated Speech-to-Text and Text-to-Speech services:

### Quick Examples

**Transcribe audio (REST API):**
```bash
curl -X POST http://localhost:8080/stt \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

**Synthesize speech (REST API):**
```bash
curl -X POST http://localhost:8080/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}' \
  --output speech.wav
```

**Full pipeline (Wyoming protocol):**
- Device sends audio via AudioStart/AudioChunk/AudioStop
- Server transcribes audio (STT)
- Server processes with agent
- Server synthesizes response (TTS)
- Device receives speech audio

See [STT/TTS Services Guide](stt_tts_services.md) for complete documentation.

## Next Steps

- Read [Architecture Documentation](architecture.md) to understand the design
- Explore [Speech Services Guide](stt_tts_services.md) for STT/TTS details
- Explore [Adding Tools](tools.md) to extend capabilities
- Check [Adapter Documentation](adapters.md) for custom protocol support
- Review [Examples](../examples/) for more use cases

## Getting Help

For issues and feature requests, see the project repository.