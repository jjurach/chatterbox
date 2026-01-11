# Cackle Agent Architecture

## Overview

Cackle is a library-first architecture for a conversational AI agent with tool use and memory capabilities. The design separates protocol-agnostic core agent logic from protocol-specific adapters, allowing the agent to be reused across multiple projects and platforms.

## Core Concepts

### Agent
The `VoiceAssistantAgent` is the central component that processes user input and generates responses using LangChain and local LLMs (via Ollama). It maintains conversation memory and can utilize tools to extend its capabilities.

**Location:** `cackle/agent.py`

### Tools
Tools are functions that the agent can invoke to perform actions like getting the current time. The tool system is centralized through a registry, making it easy to add new tools.

**Locations:**
- `cackle/tools/registry.py` - Tool registry
- `cackle/tools/builtin/` - Built-in tools like time

### Configuration
Settings are managed through environment variables and the `Settings` class, providing centralized configuration for the agent and adapters.

**Location:** `cackle/config.py`

### Adapters
Adapters provide protocol-specific implementations that integrate the core agent with different systems. Currently, Wyoming protocol adapter for ESP32 devices.

**Location:** `cackle/adapters/wyoming/`

### Observability
LangChain callback handlers provide debugging and observability into agent execution.

**Location:** `cackle/observability.py`

## Directory Structure

```
cackle/                           # Core library code (protocol-agnostic)
├── __init__.py                   # Library entry point
├── agent.py                      # Core agent implementation
├── config.py                     # Configuration management
├── observability.py              # Debugging and observability
├── tools/                        # Tool system
│   ├── __init__.py
│   ├── registry.py               # Tool registry
│   └── builtin/                  # Built-in tools
│       ├── __init__.py
│       └── time_tool.py
└── adapters/                     # Protocol adapters
    ├── __init__.py
    └── wyoming/                  # Wyoming protocol adapter
        ├── __init__.py
        ├── server.py             # Wyoming server implementation
        └── client.py             # Wyoming test client

src/                              # Application entry points
├── __init__.py
└── main.py                       # Wyoming server CLI entry point

examples/                         # Example scripts
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

```
User Input (text/audio)
    ↓
Wyoming Adapter (cackle/adapters/wyoming/)
    ↓
VoiceAssistantAgent (cackle/agent.py)
    ↓
LangChain + Ollama LLM
    ↓
Tools (cackle/tools/)
    ↓
Response → Wyoming Adapter → User Output
```

## Design Principles

1. **Protocol-Agnostic Core**: The `cackle/` directory contains only core agent logic without protocol dependencies
2. **Adapter Pattern**: Different protocols (Wyoming, HTTP, WebSocket) integrate through adapters
3. **Tool Registry**: Centralized tool discovery makes it easy to extend capabilities
4. **Configuration Management**: Environment-based settings work for both library and application usage
5. **Observability First**: Built-in debugging and logging through LangChain callbacks

## Library vs Application

### As a Library
The `cackle/` package can be imported directly:
```python
from cackle.agent import VoiceAssistantAgent
agent = VoiceAssistantAgent(...)
```

### As an Application
The `src/main.py` entry point provides the Wyoming server CLI:
```bash
chatterbox3b-server --debug
```

## Extension Points

### Adding a New Tool
1. Create a new tool module in `cackle/tools/builtin/`
2. Implement the tool function
3. Register it in `cackle/tools/registry.py`

### Adding a New Adapter
1. Create a new directory in `cackle/adapters/protocol/`
2. Implement the protocol interface
3. Export public API from `cackle/adapters/protocol/__init__.py`

### Customizing Configuration
Environment variables in `cackle/config.py` control agent behavior:
- `OLLAMA_BASE_URL` - Ollama API endpoint
- `OLLAMA_MODEL` - Model to use
- `OLLAMA_TEMPERATURE` - Response creativity (0.0-1.0)
- `CONVERSATION_WINDOW_SIZE` - Message history length

## Future Enhancements

- HTTP/REST adapter for web applications
- WebSocket adapter for real-time clients
- Plugin-based tool discovery
- Multiple LLM provider abstraction
- Persistent conversation storage
