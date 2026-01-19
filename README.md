# ESP32-S3-BOX-3B Voice Assistant with Wyoming & LangChain

A monorepo for bootstrapping a voice assistant on the ESP32-S3-BOX-3B hardware using the Wyoming protocol and LangChain for LLM orchestration.

## Project Structure

```
.
├── cackle/                       # Core library (protocol-agnostic)
│   ├── agent.py                 # VoiceAssistantAgent core
│   ├── config.py                # Configuration management
│   ├── observability.py         # Debugging & observability
│   ├── tools/                   # Tool/skill system
│   │   ├── registry.py          # Tool registry
│   │   └── builtin/             # Built-in tools
│   │       └── time_tool.py
│   └── adapters/                # Protocol adapters
│       └── wyoming/             # Wyoming protocol implementation
│           ├── server.py        # Wyoming server
│           └── client.py        # Test client
├── src/                          # Application entry point
│   └── main.py                  # Wyoming server CLI
├── examples/                     # Example scripts
│   ├── wyoming_server.py        # Running Wyoming server
│   ├── direct_agent.py          # Using agent directly
│   └── wyoming_client_test.py   # Testing Wyoming server
├── tests/                        # Test suite
│   ├── core/                    # Agent & tools tests
│   ├── adapters/                # Adapter tests
│   └── integration/             # Integration tests
├── docs/                         # Documentation
│   ├── architecture.md          # Architecture overview
│   ├── quickstart.md            # Getting started guide
│   ├── adapters.md              # Adapter documentation
│   └── tools.md                 # Tool system documentation
├── firmware/                     # ESPHome configurations
│   └── voice-assistant.yaml     # ESP32-S3-BOX-3B device config
├── pyproject.toml               # Project configuration
└── README.md                     # This file
```

## Prerequisites

- **Hardware**: ESP32-S3-BOX-3B
- **OS**: Ubuntu Workstation (or any Linux/macOS with Python 3.10+)
- **Python**: 3.10 or higher
- **ESPHome**: For flashing firmware to the device
- **pip**: Python package manager

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd chatterbox
```

### 2. Set Up Python Environment

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

Install the package with dependencies:

```bash
pip install -e .
```

For development (includes testing and linting tools):

```bash
pip install -e ".[dev]"
```

## Usage

### Prerequisites for Running the Server

Before starting the Wyoming server, you need to have Ollama running with the `llama3.1:8b` model.

#### Step 1: Install and Start Ollama

Install Ollama from [ollama.ai](https://ollama.ai) or use your package manager.

Start Ollama with the required model:

```bash
ollama run llama3.1:8b
```

This command will:
- Download the `llama3.1:8b` (Q4_K_M quantized) model if not already present
- Start the Ollama server on `http://localhost:11434`

Keep this terminal running in the background while the Wyoming server is active.

### Running the Wyoming Server

Start the Wyoming server on your Ubuntu host:

```bash
chatterbox-server
```

Or run directly with Python:

```bash
python -m src.main
```

The server will:
- Connect to Ollama on `http://localhost:11434/v1`
- Bind to `0.0.0.0:10700` and wait for connections from the ESP32-S3-BOX-3B device
- Initialize a LangChain agent with conversation memory (last 3 exchanges)
- Use the `get_time` skill to answer time-related queries

### Background Server Management

For development and testing workflows, use the background server runner script that provides reliable process management with logging:

```bash
# Start server in background
./scripts/run-server.sh start

# Check server status
./scripts/run-server.sh status

# Stop the background server
./scripts/run-server.sh stop

# Restart the server
./scripts/run-server.sh restart
```

The script features:
- **PID tracking**: Uses `./tmp/chatterbox-server.pid` to track the process
- **Comprehensive logging**: All server output logged to `./tmp/chatterbox-server.log`
- **Safe log viewing**: Instructions provided for viewing logs 10-20 lines at a time
- **Graceful shutdown**: Attempts SIGTERM before SIGKILL if needed

See [Testing with Wyoming Satellite Emulator](docs/testing-wyoming.md) for complete background server management and Wyoming testing instructions.

### Testing with the Wyoming Client

The `chatterbox-wyoming-client` CLI tool allows you to send text directly to the server as if it were a transcribed voice command, without needing the ESP32 device.

#### Basic Usage

Send a simple text query to the server:

```bash
chatterbox-wyoming-client "What time is it?"
```

#### Advanced Usage

Connect to a different host and port:

```bash
chatterbox-wyoming-client "What time is it?" --host 192.168.1.100 --port 10700
```

Enable debug logging:

```bash
chatterbox-wyoming-client "What time is it?" --debug
```

Or run the example directly:

```bash
python examples/wyoming_client_test.py "What time is it?"
```

### Testing Push-to-Talk Workflows

The `wyoming-tester` tool allows you to test full push-to-talk workflows by sending WAV audio files to a Wyoming endpoint and capturing responses.

#### Basic Usage

Send a WAV file to test push-to-talk functionality:

```bash
wyoming-tester --uri tcp://localhost:10700 --file test_tone.wav
```

This will:
- Convert the audio to Wyoming format (16kHz, 16-bit, mono)
- Send it to the Wyoming server
- Display transcription, intent, and conversation ID
- Save TTS response audio to `response.wav`

See `wyoming_tester/README.md` for detailed usage instructions.

### Debug Mode

Enable debug mode to see detailed logging of LangChain operations and Wyoming events:

```bash
chatterbox-server --debug
```

In debug mode, the server will log:

- **LangChain Debug Output**: Detailed traces of chain input, agent reasoning, and LLM decisions
- **Wyoming Events**: Timestamped events for audio streams, transcripts, and device communication
  - `AudioStart` / `AudioStop`: Audio stream lifecycle
  - `Transcript`: Speech recognition results with timestamps
  - Event timestamps in ISO 8601 format for correlation
- **LLM Usage Metrics**: Token counts and estimated costs based on cloud pricing models
  - Prompt tokens, completion tokens, total tokens
  - Estimated cost in USD (using GPT-4o-mini pricing: $0.15 per 1M input tokens, $0.60 per 1M output tokens)
  - Example output: `[LLM USAGE] Tokens: 150 | Estimated Value: $0.0002`

Example debug output:

```
2025-01-11T10:30:45.123456 - src.server - INFO - Server debug mode enabled
2025-01-11T10:30:45.234567 - src.agent - INFO - Debug mode enabled with observability logging
2025-01-11T10:30:46.345678 - src.server - INFO - [2025-01-11T10:30:46.345678] [WYOMING] AudioStart event received
2025-01-11T10:30:48.456789 - src.server - INFO - [2025-01-11T10:30:48.456789] [WYOMING] Transcript received: What time is it?
[LLM USAGE] Tokens: 42 | Estimated Value: $0.000025
```

This is useful for:
- Understanding how the agent processes inputs
- Debugging integration issues between Wyoming and LangChain
- Monitoring token usage and estimating cloud costs
- Tracing the full request/response flow

### Running Tests

Execute the test suite with pytest:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run tests with coverage:

```bash
pytest --cov=src
```

### Code Formatting

Format code with Black:

```bash
black src/ tests/
```

Sort imports with isort:

```bash
isort src/ tests/
```

## Flashing the Device

### Step 1: Find Your Ubuntu Host IP

Get your Ubuntu machine's IP address:

```bash
hostname -I
```

This will output something like: `192.168.1.100 172.17.0.1`

Use the first IP (your local network IP).

### Step 2.5: Create ESPHome Secrets File

Create a `secrets.yaml` file in the `firmware/` directory with your WiFi credentials:

```bash
cd firmware
cp secrets.yaml.example secrets.yaml
# Edit secrets.yaml with your actual WiFi credentials
```

Content of `firmware/secrets.yaml`:

```yaml
wifi_ssid: "YourWiFiNetworkName"
wifi_password: "YourWiFiPassword"
```

**Security Note**: The `secrets.yaml` file is ignored by git (included in `.gitignore`). Never commit WiFi credentials to version control.

### Step 3: Update the ESPHome Configuration

Edit `firmware/voice-assistant.yaml` and replace the placeholder:

```yaml
substitutions:
  backend_ip: "192.168.1.100"  # Use your actual IP from Step 1
```

### Step 4: Flash the Device

Install ESPHome if you haven't already:

```bash
pip install esphome
```

Flash the device via USB (make sure the device is connected):

```bash
cd firmware
esphome run voice-assistant.yaml
```

Follow the ESPHome prompts to select the USB serial port.

### Step 5: Configure Environment Variables (Optional)

For production deployments or to customize server settings, create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your custom settings
```

Available configuration options:

```env
# Server Configuration
CHATTERBOX_HOST=0.0.0.0
CHATTERBOX_PORT=10700

# Ollama Configuration
CHATTERBOX_OLLAMA_BASE_URL=http://localhost:11434/v1
CHATTERBOX_OLLAMA_MODEL=llama3.1:8b
CHATTERBOX_OLLAMA_TEMPERATURE=0.7

# Conversation Memory
CHATTERBOX_CONVERSATION_WINDOW_SIZE=3

# Logging
CHATTERBOX_LOG_LEVEL=INFO
```

### Step 6: Verify Connection

Once flashed:

1. Power on the ESP32-S3-BOX-3B
2. Ensure it's connected to the same WiFi network as your Ubuntu host
3. Start the Wyoming server: `chatterbox-server`
4. The device should connect and be ready to process voice commands

## Architecture

### Library-First Design

Cackle follows a library-first architecture separating protocol-agnostic core logic from protocol-specific adapters:

- **Core Library** (`cackle/`): Protocol-agnostic agent, tools, and configuration
- **Wyoming Adapter** (`cackle/adapters/wyoming/`): Wyoming protocol server implementation
- **Application** (`src/main.py`): Wyoming server CLI entry point

This design allows the agent to be used directly without any protocol, embedded in other applications, or integrated with different protocols.

See [Architecture Documentation](docs/architecture.md) for detailed information.

### Components

**VoiceAssistantAgent** (`cackle/agent.py`):
- Uses LangChain with Ollama for intelligent responses
- Maintains conversation memory (last N exchanges)
- Provides tool/skill system for extending capabilities

**Wyoming Adapter** (`cackle/adapters/wyoming/`):
- Listens for incoming audio streams from ESP32-S3-BOX-3B
- Processes audio using the Wyoming protocol
- Returns responses via the Wyoming protocol

**ESPHome Firmware** (`firmware/voice-assistant.yaml`):
- Configures the ESP32-S3-BOX-3B hardware (microphone, speaker, display)
- Connects to Wyoming server for audio processing
- Handles WiFi connectivity

## LangChain Integration

The backend server is fully integrated with LangChain and uses a local Ollama LLM for intelligent responses.

### Architecture

The integration includes:

1. **Language Model**: `ChatOpenAI` from `langchain_openai` connected to Ollama's OpenAI-compatible API
   - Base URL: `http://localhost:11434/v1`
   - Model: `llama3.1:8b`
   - Temperature: `0.7` (for balanced creativity and determinism)

2. **Conversation Memory**: `ConversationBufferWindowMemory` with `k=3`
   - Stores the last 3 conversational exchanges
   - Optimized for 8GB VRAM constraint
   - Prevents memory overflow while maintaining context

3. **Agent Skills**: Extensible tool system
   - **GetTime**: Provides current date and time to the agent
   - Easily add more tools by extending the `tools` list in the `__init__` method

4. **Event Processing Pipeline**:
   - Device sends audio to Wyoming server
   - Server receives transcript (text) from the device
   - LangChain agent processes the input, potentially using available skills
   - Agent response is wrapped in a TTS (Synthesize) event
   - Response is sent back to the device for audio synthesis

### Adding New Skills

To add a new skill/tool:

```python
# 1. Define the tool function
def my_skill(param: str) -> str:
    """Tool description for the agent."""
    return "result"

# 2. Add it to the tools list in VoiceAssistantServer.__init__:
tools = [
    Tool(
        name="MySkill",
        func=my_skill,
        description="What the agent can use this for.",
    ),
    # ... other tools
]
```

### Model Performance Notes

- **Model**: llama3.1:8b with Q4_K_M quantization (4-bit quantization)
- **VRAM**: Optimized for RTX 2080 (8GB) with ConversationBufferWindowMemory window of 3
- **Response Time**: Typical response time is 2-5 seconds depending on query complexity
- **Accuracy**: llama3.1 is well-suited for general conversational AI and tool use

## Development

### Setting Up Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. Set them up with:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Run against all files (optional)
pre-commit run --all-files
```

The hooks will automatically run on `git commit` and check for:
- Code formatting (Black, isort)
- Linting (flake8, mypy)
- Common issues (trailing whitespace, large files, etc.)

### Project Structure Best Practices

- Use `src/` directory for the main application code
- Keep tests in `tests/`
- Use type hints (Python 3.10+)
- Follow PEP 8 with Black for formatting

### Adding Dependencies

For production dependencies, add to `requirements.txt`:

```bash
pip install <package-name>
pip freeze > requirements.txt
```

For development-only dependencies, add to `requirements-dev.txt`.

## Troubleshooting

### Ollama Connection Failed

If the Wyoming server fails to connect to Ollama:

1. **Verify Ollama is Running**:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   Should return a JSON list of available models.

2. **Check if the Model is Downloaded**:
   ```bash
   ollama list
   ```
   Should show `llama3.1:8b` in the list.

3. **Start Ollama if Not Running**:
   ```bash
   ollama run llama3.1:8b
   ```

4. **Check Logs**: The Wyoming server logs will show connection errors. Look for messages like `Connection refused` which indicate Ollama is not accessible.

### Device Won't Connect

- Verify the `backend_ip` in `firmware/voice-assistant.yaml` matches your Ubuntu host
- Ensure both devices are on the same WiFi network
- Check firewall settings on Ubuntu (port 10700 should be open)
- Verify the Wyoming server is running: `chatterbox-server`
- Verify Ollama is running in a separate terminal: `ollama run llama3.1:8b`

### Server Port Already in Use

If port 10700 is already in use, set the environment variable before running the server:

```bash
CHATTERBOX_PORT=9999 chatterbox-server
```

Update the port in `firmware/voice-assistant.yaml` accordingly.

### Serial Port Issues During Flashing

On Linux, you may need to add your user to the dialout group:

```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

## Resources

- [Wyoming Protocol Documentation](https://www.rhasspy.org/wyoming/)
- [ESPHome Documentation](https://esphome.io/)
- [LangChain Documentation](https://python.langchain.com/)
- [ESP32-S3-BOX-3B Hardware Reference](https://github.com/espressif/esp-box)

## License

[Specify your license here]

## Contributing

[Add contributing guidelines here]