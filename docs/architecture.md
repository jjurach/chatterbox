# Chatterbox Agent Architecture

## Overview

Chatterbox is a library-first architecture for a conversational AI agent with tool use and memory capabilities. The design separates protocol-agnostic core agent logic from protocol-specific adapters, allowing the agent to be reused across multiple projects and platforms.

## Core Concepts

### Agent
The `VoiceAssistantAgent` is the central component that processes user input and generates responses using LangChain and local LLMs (via Ollama). It maintains conversation memory and can utilize tools to extend its capabilities.

**Location:** `src/chatterbox/agent.py`

### STT/TTS Services
Dedicated services for speech processing:
- **WhisperSTTService**: Speech-to-text transcription using OpenAI Whisper
- **PiperTTSService**: Text-to-speech synthesis using Piper TTS

These services can be used independently or integrated with the Wyoming protocol and REST API.

**Location:** `src/chatterbox/services/`

### Tools
Tools are functions that the agent can invoke to perform actions like getting the current time, transcribing audio, or synthesizing speech. The tool system is centralized through a registry, making it easy to add new tools.

**Locations:**
- `src/chatterbox/tools/registry.py` - Tool registry
- `src/chatterbox/tools/builtin/` - Built-in tools (time, STT, TTS)

### Configuration
Settings are managed through environment variables and the `Settings` class, providing centralized configuration for the agent, adapters, and services.

**Location:** `src/chatterbox/config.py`

### Adapters
Adapters provide protocol-specific implementations that integrate the core agent with different systems.

**Available adapters:**
- **Wyoming** (`src/chatterbox/adapters/wyoming/`) - ESP32 and voice assistant protocol
- **REST** (`src/chatterbox/adapters/rest/`) - HTTP JSON API with FastAPI

### Observability
LangChain callback handlers provide debugging and observability into agent execution.

**Location:** `src/chatterbox/observability.py`

## Directory Structure

```
src/                              # Source code (installable packages)
├── __init__.py
├── main.py                       # Wyoming server CLI entry point
├── chatterbox/                   # Core library code (protocol-agnostic)
│   ├── __init__.py               # Library entry point
│   ├── agent.py                  # Core agent implementation
│   ├── config.py                 # Configuration management
│   ├── observability.py          # Debugging and observability
│   ├── services/                 # STT and TTS services
│   │   ├── __init__.py
│   │   ├── stt.py                # Whisper STT service
│   │   └── tts.py                # Piper TTS service
│   ├── tools/                    # Tool system
│   │   ├── __init__.py
│   │   ├── registry.py           # Tool registry
│   │   └── builtin/              # Built-in tools
│   │       ├── __init__.py
│   │       ├── time_tool.py
│   │       ├── stt_tool.py       # STT tool for agents
│   │       └── tts_tool.py       # TTS tool for agents
│   └── adapters/                 # Protocol adapters
│       ├── __init__.py
│       ├── wyoming/              # Wyoming protocol adapter
│       │   ├── __init__.py
│       │   ├── server.py         # Wyoming server implementation
│       │   └── client.py         # Wyoming test client
│       └── rest/                 # REST API adapter
│           ├── __init__.py
│           └── api.py            # FastAPI application
└── wyoming_tester/               # Wyoming test utility
    ├── __init__.py
    ├── cli.py                    # Command-line interface
    ├── audio.py                  # Audio utilities
    └── protocol.py               # Protocol helpers

demos/                            # Example scripts
├── wyoming_server.py             # Running Wyoming server
├── direct_agent.py               # Using agent directly
└── wyoming_client_test.py        # Testing Wyoming server

tests/                            # Test suite
├── __init__.py
├── conftest.py
├── core/                         # Core agent tests
│   ├── __init__.py
│   ├── test_agent.py
│   └── test_tools.py
├── adapters/                     # Adapter tests
│   ├── __init__.py
│   └── wyoming/
│       ├── __init__.py
│       └── test_server.py
└── integration/                  # Integration tests
    ├── __init__.py
    └── test_end_to_end.py

docs/                             # Documentation
├── architecture.md               # This file
├── quickstart.md                 # Getting started guide
├── adapters.md                   # Adapter documentation
└── tools.md                      # Tool system documentation
```

## Component Interaction

### Full Voice Assistant Flow (Mode: `full`)
```
Audio Input
    ↓
Wyoming/REST → STT Service (Whisper)
    ↓
Transcript → VoiceAssistantAgent
    ↓
LangChain + Ollama LLM
    ↓
Tools (get_time, transcribe_audio, synthesize_speech)
    ↓
Response → TTS Service (Piper)
    ↓
Audio Output → Wyoming/REST
```

### STT-Only Flow (Mode: `stt_only`)
```
Audio Input
    ↓
Wyoming/REST → STT Service (Whisper)
    ↓
Transcript Output → Client
```

### TTS-Only Flow (Mode: `tts_only`)
```
Text Input
    ↓
Wyoming/REST → TTS Service (Piper)
    ↓
Audio Output → Client
```

### Adapter Integration
```
Wyoming Protocol Client (ESP32, HA)
        ↓
    Wyoming Server (src/chatterbox/adapters/wyoming/)
        ↓ ↓ ↓
    STT  AGENT  TTS
    Services
        ↓
    REST API Client
        ↓
    FastAPI (src/chatterbox/adapters/rest/)
```

## Design Principles

1. **Protocol-Agnostic Core**: The `src/chatterbox/` directory contains only core agent logic without protocol dependencies
2. **Adapter Pattern**: Different protocols (Wyoming, HTTP, WebSocket) integrate through adapters
3. **Tool Registry**: Centralized tool discovery makes it easy to extend capabilities
4. **Configuration Management**: Environment-based settings work for both library and application usage
5. **Observability First**: Built-in debugging and logging through LangChain callbacks

## Library vs Application

### As a Library
The `src/chatterbox/` package can be imported directly:
```python
from chatterbox.agent import VoiceAssistantAgent
agent = VoiceAssistantAgent(...)
```

### As an Application
The `src/main.py` entry point provides the Wyoming server CLI:
```bash
chatterbox-server --debug
```

## Extension Points

### Adding a New Tool
1. Create a new tool module in `src/chatterbox/tools/builtin/`
2. Implement the tool function
3. Register it in `src/chatterbox/tools/registry.py`

### Adding a New Adapter
1. Create a new directory in `src/chatterbox/adapters/protocol/`
2. Implement the protocol interface
3. Export public API from `src/chatterbox/adapters/protocol/__init__.py`

### Customizing Configuration
Environment variables in `src/chatterbox/config.py` control agent behavior:
- `OLLAMA_BASE_URL` - Ollama API endpoint
- `OLLAMA_MODEL` - Model to use
- `OLLAMA_TEMPERATURE` - Response creativity (0.0-1.0)
- `CONVERSATION_WINDOW_SIZE` - Message history length

## Service Modes

The server can operate in different modes optimized for different use cases:

| Mode | Components | Use Case |
|------|-----------|----------|
| `full` | Agent + STT + TTS | Complete voice assistant with agent intelligence |
| `stt_only` | STT only | Dedicated transcription service |
| `tts_only` | TTS only | Dedicated speech synthesis service |
| `combined` | STT + TTS (no Agent) | Audio processing without LLM inference |

## Future Enhancements

- WebSocket adapter for real-time streaming
- Plugin-based tool discovery system
- Multiple LLM provider abstraction
- Persistent conversation storage
- Vision and other multimodal services
- Performance optimization (batching, caching)

---
Last Updated: 2026-02-01
